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
});

// Function to generate date options for the next 14 days
function generateDateOptions() {
    const dateSelect = document.getElementById('appointment_date');
    const today = new Date();

    for (let i = 0; i < 14; i++) {
        const date = new Date();
        date.setDate(today.getDate() + i);

        const option = document.createElement('option');
        option.value = date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
        option.textContent = date.toDateString(); // Format as a readable date string

        dateSelect.appendChild(option);
    }
}


document.addEventListener("DOMContentLoaded", function () {
    const addActivityButton = document.getElementById("addActivityButton");
    const activityForm = document.getElementById("activityForm");
    const activityText = document.getElementById("activityText");
    const cancelButton = document.getElementById("cancelButton");
    const activityEventsList = document.getElementById("activityEventsList");
    const addActivityTitle = document.getElementById("addActivityTitle");

    function handleFormSubmission(event) {
        event.preventDefault();

        const newActivityText = activityText.value;

        const newActivityItem = document.createElement("li");
        newActivityItem.textContent = newActivityText;

        activityEventsList.appendChild(newActivityItem);

        activityText.value = "";

        activityForm.classList.remove("active");
        addActivityButton.style.display = "block";
        if (addActivityTitle) {
            addActivityTitle.style.display = "block";
        }
    }

    addActivityButton.addEventListener("click", function () {
        activityForm.classList.add("active");
        addActivityButton.style.display = "none";
        if (addActivityTitle) {
            addActivityTitle.style.display = "none";
        }
    });

    cancelButton.addEventListener("click", function () {
        activityForm.classList.remove("active");
        addActivityButton.style.display = "block";
        if (addActivityTitle) {
            addActivityTitle.style.display = "block";
        }
    });

    activityForm.addEventListener("submit", handleFormSubmission);
});

// Get the modal
var modal = document.getElementById("editModal");

// Get the button that opens the modal
var btn = document.getElementById("editBtn");

// Get the <span> element that closes the modal
var span = document.getElementsByClassName("close")[0];

// When the user clicks the button, open the modal 
btn.onclick = function () {
    modal.style.display = "block";
}

// When the user clicks on <span> (x), close the modal
span.onclick = function () {
    modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

document.getElementById('profile_photo').addEventListener('change', function () {
    var fileName = this.value.split('\\').pop();
    var label = this.nextElementSibling;
    label.innerText = fileName ? fileName : 'Choose File';
});

// Event listener for the remove photo button
document.getElementById('removePhotoBtn').addEventListener('click', function () {
    var checkbox = document.getElementById('remove_photo');
    checkbox.checked = !checkbox.checked;
    this.classList.toggle('active');
    if (checkbox.checked) {
        this.innerText = 'Undo';
        this.style.backgroundColor = '#b4b4b4';
    } else {
        this.innerText = 'Remove';
        this.style.backgroundColor = '';
    }
});
