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
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

message_scheduler = Blueprint('message_scheduler', __name__)

def is_valid_phone_number(phone_number):
    pattern = r'^\+[1-9]\d{1,14}$'
    return re.match(pattern, phone_number) is not None

@message_scheduler.route('/dashboard')
@login_required
def dashboard():
    scheduled_blasts = ScheduledBlast.query.filter_by(user_id=current_user.id).all()
    for blast in scheduled_blasts:
        blast.recipient_count = len(blast.recipient_associations)
        blast.status_color = {
            'scheduled': 'primary',
            'sent': 'success',
            'canceled': 'danger',
            'failed': 'warning'
        }.get(blast.status, 'secondary')
    return render_template('dashboard.html', scheduled_blasts=scheduled_blasts)

@message_scheduler.route('/schedule_blast', methods=['GET', 'POST'])
@login_required
def schedule_blast():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        message_template = request.form['message_template']
        mms_url = request.form.get('mms_url')
        scheduled_time = datetime.strptime(request.form['scheduled_time'], '%Y-%m-%dT%H:%M')
        
        eastern = pytz.timezone('US/Eastern')
        scheduled_time_et = eastern.localize(scheduled_time)
        scheduled_time_utc = scheduled_time_et.astimezone(pytz.UTC)

        now_utc = datetime.now(pytz.UTC)
        if scheduled_time_utc <= now_utc + timedelta(minutes=15):
            flash('Scheduled time must be at least 15 minutes in the future.', 'danger')
            return redirect(url_for('message_scheduler.schedule_blast'))

        if scheduled_time_utc > now_utc + timedelta(days=7):
            flash('Scheduled time must be within 7 days from now.', 'danger')
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
                mms_url=mms_url,
                scheduled_time=scheduled_time_utc,
                status='scheduled'
            )
            db.session.add(new_blast)
            db.session.flush()
            logger.info(f"Created new ScheduledBlast with ID: {new_blast.id}")

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
                    logger.info(f"Created new Recipient with phone number: {phone_number}")
                else:
                    recipient.name = row.get('name', recipient.name)
                    recipient.email = row.get('email', recipient.email)
                    recipient.custom_fields.update({k: v for k, v in row.items() if k not in ['phone_number', 'name', 'email']})
                    logger.info(f"Updated existing Recipient with phone number: {phone_number}")

                db.session.flush()

                association = RecipientBlastAssociation(
                    recipient_id=recipient.id,
                    scheduled_blast_id=new_blast.id
                )
                db.session.add(association)
                logger.info(f"Created RecipientBlastAssociation for Recipient ID: {recipient.id} and ScheduledBlast ID: {new_blast.id}")

            if invalid_phone_numbers:
                flash(f'The following phone numbers are invalid and were skipped: {", ".join(invalid_phone_numbers)}', 'warning')

            db.session.commit()
            logger.info(f"Committed changes to database for ScheduledBlast ID: {new_blast.id}")

            twilio_message_sids = schedule_twilio_message(new_blast)
            if twilio_message_sids:
                new_blast.twilio_message_sid = twilio_message_sids
                db.session.commit()
                flash('Message blast scheduled successfully!', 'success')
                logger.info(f"Successfully scheduled Twilio messages for ScheduledBlast ID: {new_blast.id}")
            else:
                db.session.rollback()
                flash('Failed to schedule message blast with Twilio.', 'danger')
                logger.error(f"Failed to schedule Twilio messages for ScheduledBlast ID: {new_blast.id}")
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling message blast: {str(e)}', 'danger')
            logger.error(f"Error scheduling message blast: {str(e)}")

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
            logger.info(f"Successfully canceled ScheduledBlast ID: {blast_id}")
        else:
            flash('Failed to cancel the message blast with Twilio.', 'danger')
            logger.error(f"Failed to cancel ScheduledBlast ID: {blast_id} with Twilio")
    else:
        flash('This blast cannot be canceled.', 'warning')
    
    return redirect(url_for('message_scheduler.dashboard'))

app.register_blueprint(message_scheduler)
