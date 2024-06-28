// Event listener for DOMContentLoaded to ensure the document is fully loaded before executing the script
document.addEventListener('DOMContentLoaded', () => {
    const dateTimeElement = document.getElementById('date-time');

    // Function to update the current date and time every second
    function updateDateTime() {
        const now = new Date();
        const options = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        };
        dateTimeElement.textContent = now.toLocaleDateString('en-US', options);
    }

    // Update date and time every second
    setInterval(updateDateTime, 1000);
    updateDateTime();

    generateDateOptions(); // Ensure date options are generated on page load

    const doctorSelect = document.getElementById('doctor');
    const dateSelect = document.getElementById('appointment_date');

    doctorSelect.addEventListener('change', fetchAvailableTimes);
    dateSelect.addEventListener('change', fetchAvailableTimes);
});

// Function to generate date options starting from tomorrow for the next 14 days
function generateDateOptions() {
    const dateSelect = document.getElementById('appointment_date');
    const today = new Date();

    // Start from tomorrow
    today.setDate(today.getDate() + 1);

    for (let i = 0; i < 14; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);

        const option = document.createElement('option');
        option.value = date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
        option.textContent = date.toDateString(); // Format as a readable date string

        dateSelect.appendChild(option);
    }
}

// Function to fetch available times for the selected doctor and date
function fetchAvailableTimes() {
    const doctorId = document.getElementById('doctor').value;
    const appointmentDate = document.getElementById('appointment_date').value;

    if (doctorId && appointmentDate) {
        fetch('/get_available_times', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                doctor_id: doctorId,
                appointment_date: appointmentDate
            })
        })
            .then(response => response.json())
            .then(data => {
                const timeSelect = document.getElementById('appointment_time');
                timeSelect.innerHTML = ''; // Clear existing options

                if (data.error) {
                    alert(data.error);
                    return;
                }

                const availableTimes = data.available_times;

                availableTimes.forEach(time => {
                    const option = document.createElement('option');
                    option.value = time;
                    option.textContent = time;
                    timeSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error fetching available times:', error);
            });
    }
}

// Function to toggle the display of the appointment form
function toggleAppointmentForm() {
    const appointmentCard = document.getElementById('appointmentCard');
    if (appointmentCard.style.transform === 'rotateY(0deg)') {
        appointmentCard.style.transform = 'rotateY(-180deg)';
    } else {
        appointmentCard.style.transform = 'rotateY(0deg)';
    }
}

// Function to handle form submission and hide the input container
function handleSubmit() {
    const input = document.getElementById('userInput').value;
    if (input) {
        alert('Submitted: ' + input);
        toggleInputContainer(); // Hide the input container after submission
    }
    else {
        alert("Please, Write your situation before submitting.");
    }
}

// Function to toggle the display of the input container
function toggleInputContainer() {
    const helpCard = document.getElementById('helpCard');
    if (helpCard.style.transform === 'rotateY(-180deg)') {
        helpCard.style.transform = 'rotateY(0deg)';
    } else {
        helpCard.style.transform = 'rotateY(-180deg)';
    }
}

// Function to show the Download and Cancel buttons and hide the Get it! button
function showDownloadCancel() {
    document.getElementById('getItButton').classList.add('hidden');
    document.getElementById('downloadButton').classList.remove('hidden');
    document.getElementById('cancelButton').classList.remove('hidden');
}

// Function to reset the button visibility to its original state
function resetButtons() {
    document.getElementById('getItButton').classList.remove('hidden');
    document.getElementById('downloadButton').classList.add('hidden');
    document.getElementById('cancelButton').classList.add('hidden');
}

// Function to handle the cancel action for the appointment card
function cancelAppointment() {
    toggleAppointmentForm();
}

function reserveAppointment() {
    const doctor = document.getElementById('doctor').value;
    const appointmentDate = document.getElementById('appointment_date').value;
    const appointmentTime = document.getElementById('appointment_time').value;

    if (doctor && appointmentDate && appointmentTime) {
        toggleAppointmentForm();
    }
}
