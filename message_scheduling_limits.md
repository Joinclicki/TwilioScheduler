# Message Scheduling Limits

## Current Implementation

1. Minimum scheduling time: 15 minutes in the future
   - Implemented in `schedule_blast` function:
     ```python
     if scheduled_time_utc <= now_utc + timedelta(minutes=15):
         flash('Scheduled time must be at least 15 minutes in the future.', 'danger')
     ```

2. Maximum scheduling time: 35 days from now
   - Implemented in `schedule_blast` function:
     ```python
     if scheduled_time_utc > now_utc + timedelta(days=35):
         flash('Scheduled time must be within 35 days from now.', 'danger')
     ```

3. Phone number validation: E.164 format
   - Implemented in `is_valid_phone_number` function:
     ```python
     pattern = r'^\+[1-9]\d{1,14}$'
     return re.match(pattern, phone_number) is not None
     ```

## Twilio's Official Limits

According to Twilio's documentation:

1. Minimum scheduling time: 15 minutes in the future
   - Our implementation matches Twilio's requirement.

2. Maximum scheduling time: 7 days (168 hours) from now
   - Our implementation allows for a longer period (35 days) than Twilio's limit. We should update this to match Twilio's requirement.

3. Phone number validation: E.164 format
   - Our implementation matches Twilio's requirement.

4. Maximum number of scheduled messages: 500,000 per account
   - We haven't implemented this limit in our application. We should consider adding this check.

## Recommendations

1. Update the maximum scheduling time to 7 days to match Twilio's limit.
2. Implement a check for the maximum number of scheduled messages per account (500,000).
3. Consider implementing rate limiting to prevent abuse of the scheduling feature.
4. Add error handling for Twilio API limits and errors in the `schedule_twilio_message` function.

## Additional Considerations

1. Message content limits: Twilio has specific character limits for SMS and MMS messages. We should validate message length before scheduling.
2. Recipient limits: Consider implementing a limit on the number of recipients per blast to prevent accidental mass messaging.
3. Messaging costs: Implement a system to track and manage messaging costs, especially for large-scale blasts.

These limits and considerations should be clearly communicated to users in the application's documentation and user interface.
