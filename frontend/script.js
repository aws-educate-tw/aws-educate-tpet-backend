document.getElementById('emailForm').addEventListener('submit', function (event) {
    event.preventDefault(); // Prevent form from reloading the page after submission

    const templateFileId = document.getElementById('templateFileId').value;
    const spreadsheetId = document.getElementById('spreadsheetId').value;
    const emailTitle = document.getElementById('emailTitle').value; // Retrieve the value of email title
    const apiEndpoint = 'https://yo5206a7p0.execute-api.ap-northeast-1.amazonaws.com/default/email-service-dev-sendEmail';
    const submitButton = document.querySelector('button');

    // Disable the button to prevent multiple submissions
    submitButton.disabled = true;
    submitButton.textContent = 'Sending...';

    // Build query parameters
    const queryParams = new URLSearchParams({
        template_file_id: templateFileId,
        spreadsheet_id: spreadsheetId,
        email_title: emailTitle // Add email title to the query parameters
    });

    // Send a GET request to the API
    fetch(`${apiEndpoint}?${queryParams}`)
        .then(response => {
            if (response.ok) { // If the status code is 200-299
                return response.json().then(data => {
                    alert('Email sent successfully!');
                    submitButton.disabled = false;
                    submitButton.textContent = 'Send API Request';
                    console.log(data); // Log the returned data
                });
            } else {
                // Handle non-200 status codes
                return response.json().then(data => {
                    alert('Error: ' + data.message);
                    submitButton.disabled = false;
                    submitButton.textContent = 'Send API Request';
                });
            }
        })
        .catch(error => {
            console.error('Error making API request:', error);
            alert('API request failed: ' + error.message);
            submitButton.disabled = false;
            submitButton.textContent = 'Send API Request';
        });
});