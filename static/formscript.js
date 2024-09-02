$(document).ready(function() {
    // Function to toggle the visibility of the sibling form
    function toggleForm(button, form) {
        // Hide all forms
        $('.form-container form').hide();

        // Toggle the target form
        $(form).toggle();
    }

    // Event listener for the "Make a New Entry" button
    $('#newEntryButton').click(function() {
        toggleForm(this, '#newEntryForm');
    });

    // Event listener for the "Edit a Previous Entry" button
    $('#editButton').click(function() {
        toggleForm(this, '#editForm');
    });

    // Handle form submission via AJAX
    $("form").submit(function(event) {
        event.preventDefault();  // Prevent the default form submission

        var formData = new FormData(this);
        var token = localStorage.getItem("token");

        $.ajax({
            url: "/submit",
            type: "POST",
            headers: {
                "Authorization": "Bearer " + token,
            },
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                if (data.message) {
                    alert(data.message);  // Show success message
                } else {
                    alert("Submission failed.");
                }
            }
        });
    });
});
