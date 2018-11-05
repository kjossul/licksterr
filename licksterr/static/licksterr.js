function addUploadListener() {
    const button = document.getElementById("uploadBtn");
    button.addEventListener("click", function (e) {
        e.preventDefault();
        const file = document.getElementById("uploadFile").files[0];
        uploadFile(file);
        document.getElementById('uploadPlaceholder').innerText = "Waiting for server..."
    });
}

function uploadFile(file) {
    var fd = new FormData();
    fd.append("tab", file);

    $.ajax({
        url: "/upload",
        type: "POST",
        data: fd,
        processData: false,
        contentType: false,
        success: function (response) {
            window.location.reload();
        },
        error: function (jqXHR, textStatus, errorMessage) {
            console.log(errorMessage); // Optional
        }
    });
}

addEventListener("DOMContentLoaded", function () {
    addUploadListener();
}, true);