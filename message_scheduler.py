from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import ScheduledBlast, Recipient, RecipientBlastAssociation, db
from twilio_integration import schedule_twilio_message, cancel_twilio_message
from io import StringIO
import csv
from datetime import datetime, timedelta
import pytz
from app import app
import re

message_scheduler = Blueprint('message_scheduler', __name__)

def is_valid_phone_number(phone_number):
    # Basic E.164 format validation
    pattern = r'^\+[1-9]\d{1,14}$'
    return re.match(pattern, phone_number) is not None

@message_scheduler.route('/dashboard')
@login_required
def dashboard():
    scheduled_blasts = ScheduledBlast.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', scheduled_blasts=scheduled_blasts)

@message_scheduler.route('/schedule_blast', methods=['GET', 'POST'])
@login_required
def schedule_blast():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        message_template = request.form['message_template']
        scheduled_time = datetime.strptime(request.form['scheduled_time'], '%Y-%m-%dT%H:%M')
        
        # Convert to Eastern Time
        eastern = pytz.timezone('US/Eastern')
        scheduled_time_et = eastern.localize(scheduled_time)
        
        # Convert to UTC
        scheduled_time_utc = scheduled_time_et.astimezone(pytz.UTC)

        now_utc = datetime.now(pytz.UTC)
        if scheduled_time_utc <= now_utc + timedelta(minutes=15):
            flash('Scheduled time must be at least 15 minutes in the future.', 'danger')
            return redirect(url_for('message_scheduler.schedule_blast'))

        if scheduled_time_utc > now_utc + timedelta(days=35):
            flash('Scheduled time must be within 35 days from now.', 'danger')
            return redirect(url_for('message_scheduler.schedule_blast'))

        try:
            csv_content = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(StringIO(csv_content))
            
            if 'phone_number' not in csv_data.fieldnames:
                flash('CSV file must contain a "phone_number" column.', 'danger')
                return redirect(url_for('message_scheduler.schedule_blast'))

            new_blast = ScheduledBlast(
                user_id=current_user.id,
                message_template=message_template,
                scheduled_time=scheduled_time_utc,
                status='scheduled'
            )
            db.session.add(new_blast)
            db.session.flush()  # This assigns an ID to new_blast

            invalid_phone_numbers = []
            for row in csv_data:
                phone_number = row.get('phone_number', '').strip()
                if not phone_number or not is_valid_phone_number(phone_number):
                    invalid_phone_numbers.append(phone_number)
                    continue

                recipient = Recipient.query.filter_by(phone_number=phone_number).first()
                if not recipient:
                    recipient = Recipient(
                        phone_number=phone_number,
                        name=row.get('name', ''),
                        email=row.get('email', ''),
                        custom_fields={k: v for k, v in row.items() if k not in ['phone_number', 'name', 'email']}
                    )
                    db.session.add(recipient)
                else:
                    # Update existing recipient's information
                    recipient.name = row.get('name', recipient.name)
                    recipient.email = row.get('email', recipient.email)
                    recipient.custom_fields.update({k: v for k, v in row.items() if k not in ['phone_number', 'name', 'email']})

                db.session.flush()  # This assigns an ID to recipient if it's new

                association = RecipientBlastAssociation(
                    recipient_id=recipient.id,
                    scheduled_blast_id=new_blast.id
                )
                db.session.add(association)

            if invalid_phone_numbers:
                flash(f'The following phone numbers are invalid and were skipped: {", ".join(invalid_phone_numbers)}', 'warning')

            db.session.commit()  # Commit the changes before scheduling with Twilio

            twilio_message_sid = schedule_twilio_message(new_blast)
            if twilio_message_sid:
                new_blast.twilio_message_sid = twilio_message_sid
                db.session.commit()
                flash('Message blast scheduled successfully!', 'success')
            else:
                db.session.rollback()
                flash('Failed to schedule message blast with Twilio.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling message blast: {str(e)}', 'danger')

        return redirect(url_for('message_scheduler.dashboard'))

    return render_template('schedule_blast.html')

@message_scheduler.route('/preview_csv', methods=['POST'])
@login_required
def preview_csv():
    csv_file = request.files.get('csv_file')
    if csv_file:
        try:
            csv_content = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(StringIO(csv_content))
            headers = csv_data.fieldnames
            return jsonify({'headers': headers})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    return jsonify({'error': 'No CSV file provided'}), 400

@message_scheduler.route('/cancel_blast/<int:blast_id>', methods=['POST'])
@login_required
def cancel_blast(blast_id):
    blast = ScheduledBlast.query.get_or_404(blast_id)
    if blast.user_id != current_user.id:
        flash('You are not authorized to cancel this blast.', 'danger')
        return redirect(url_for('message_scheduler.dashboard'))
    
    if blast.status == 'scheduled':
        if cancel_twilio_message(blast.twilio_message_sid):
            blast.status = 'canceled'
            db.session.commit()
            flash('Message blast canceled successfully.', 'success')
        else:
            flash('Failed to cancel the message blast with Twilio.', 'danger')
    else:
        flash('This blast cannot be canceled.', 'warning')
    
    return redirect(url_for('message_scheduler.dashboard'))

# Register the blueprint with the Flask app
app.register_blueprint(message_scheduler)
