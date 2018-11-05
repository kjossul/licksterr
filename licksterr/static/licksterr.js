function addUploadListener() {
    const button = document.getElementById("uploadBtn");
    button.addEventListener("click", function (e) {
        e.preventDefault();
        let tracks = [];
        $('.track-checkbox').each(function (i, obj) {
            if (obj.checked) {
                tracks.push(obj.value);
            }
        });
        const file = document.getElementById("uploadFile").files[0];
        uploadFile(file, tracks);
        $('#uploadPlaceholder').innerText = "Waiting for server..."
    });
}

function uploadFile(file, tracks) {
    var fd = new FormData();
    fd.append("tab", file);
    fd.append("tracks", JSON.stringify(tracks));
    let is_analysis = tracks.length > 0;
    $.ajax({
        url: (is_analysis) ? "/upload" : "/tabinfo",
        type: "POST",
        data: fd,
        processData: false,
        contentType: false,
        success: function (response) {
            if (is_analysis) {
                window.location.reload();
            } else {
                var $container = $('#trackSelect');
                for (let [key, value] of Object.entries(response)) {
                    $container.append($('<label />').html(value)
                        .prepend($('<input/>').attr({type: 'checkbox', value: key, class: 'track-checkbox'})));
                }
                $('#uploadPlaceholder').innerText = '';
            }
        },
        error: function (jqXHR, textStatus, errorMessage) {
            console.log(errorMessage); // Optional
        }
    });
}

addEventListener("DOMContentLoaded", function () {
    addUploadListener();
}, true);