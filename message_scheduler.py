from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import ScheduledBlast, Recipient, RecipientBlastAssociation, db
from twilio_integration import schedule_twilio_message
from io import StringIO
import csv
from datetime import datetime, timedelta
from app import app

message_scheduler = Blueprint('message_scheduler', __name__)

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

        if scheduled_time <= datetime.now() + timedelta(minutes=15):
            flash('Scheduled time must be at least 15 minutes in the future.', 'danger')
            return redirect(url_for('message_scheduler.schedule_blast'))

        if scheduled_time > datetime.now() + timedelta(days=35):
            flash('Scheduled time must be within 35 days from now.', 'danger')
            return redirect(url_for('message_scheduler.schedule_blast'))

        try:
            csv_content = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(StringIO(csv_content))
            
            new_blast = ScheduledBlast(
                user_id=current_user.id,
                message_template=message_template,
                scheduled_time=scheduled_time,
                status='scheduled'
            )
            db.session.add(new_blast)
            db.session.flush()  # This assigns an ID to new_blast

            for row in csv_data:
                recipient = Recipient(
                    phone_number=row['phone_number'],
                    name=row.get('name', ''),
                    email=row.get('email', ''),
                    custom_fields={k: v for k, v in row.items() if k not in ['phone_number', 'name', 'email']}
                )
                db.session.add(recipient)
                db.session.flush()  # This assigns an ID to recipient

                association = RecipientBlastAssociation(
                    recipient_id=recipient.id,
                    scheduled_blast_id=new_blast.id
                )
                db.session.add(association)

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
        from twilio_integration import cancel_twilio_message
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
