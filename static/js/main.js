document.addEventListener('DOMContentLoaded', function() {
    const scheduleBlastForm = document.getElementById('scheduleBlastForm');
    
    if (scheduleBlastForm) {
        scheduleBlastForm.addEventListener('submit', function(event) {
            const csvFile = document.getElementById('csv_file');
            const messageTemplate = document.getElementById('message_template');
            const scheduledTime = document.getElementById('scheduled_time');
            
            let isValid = true;
            
            // Validate CSV file
            if (csvFile.files.length === 0) {
                alert('Please upload a CSV file.');
                isValid = false;
            } else if (!csvFile.files[0].name.endsWith('.csv')) {
                alert('Please upload a valid CSV file.');
                isValid = false;
            }
            
            // Validate message template
            if (messageTemplate.value.trim() === '') {
                alert('Please enter a message template.');
                isValid = false;
            }
            
            // Validate scheduled time
            const now = new Date();
            const selectedTime = new Date(scheduledTime.value);
            const minTime = new Date(now.getTime() + 15 * 60000); // 15 minutes from now
            const maxTime = new Date(now.getTime() + 35 * 24 * 60 * 60000); // 35 days from now
            
            if (selectedTime < minTime) {
                alert('Scheduled time must be at least 15 minutes in the future.');
                isValid = false;
            } else if (selectedTime > maxTime) {
                alert('Scheduled time must be within 35 days from now.');
                isValid = false;
            }
            
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
});
