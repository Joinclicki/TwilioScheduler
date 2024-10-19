document.addEventListener('DOMContentLoaded', function() {
    const scheduleBlastForm = document.getElementById('scheduleBlastForm');
    const csvFileInput = document.getElementById('csv_file');
    const messageTemplate = document.getElementById('message_template');
    const fieldPicker = document.getElementById('field_picker');
    
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

    if (csvFileInput) {
        csvFileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const formData = new FormData();
                formData.append('csv_file', file);

                fetch('/preview_csv', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.headers) {
                        updateFieldPicker(data.headers);
                    } else {
                        console.error('Error:', data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            }
        });
    }

    if (fieldPicker) {
        fieldPicker.addEventListener('change', function(event) {
            const selectedField = event.target.value;
            if (selectedField) {
                insertFieldIntoTemplate(selectedField);
            }
        });
    }

    function updateFieldPicker(headers) {
        fieldPicker.innerHTML = '<option value="">Select a field</option>';
        headers.forEach(header => {
            const option = document.createElement('option');
            option.value = header;
            option.textContent = header;
            fieldPicker.appendChild(option);
        });
        fieldPicker.disabled = false;
    }

    function insertFieldIntoTemplate(field) {
        const cursorPos = messageTemplate.selectionStart;
        const textBefore = messageTemplate.value.substring(0, cursorPos);
        const textAfter = messageTemplate.value.substring(cursorPos);
        messageTemplate.value = textBefore + `{${field}}` + textAfter;
        messageTemplate.focus();
        messageTemplate.selectionStart = cursorPos + field.length + 2;
        messageTemplate.selectionEnd = messageTemplate.selectionStart;
    }
});
