/* HOMEPAGE */

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

function addRemoveListener() {
    $('.remove-song-button').each(function (i, obj) {
        obj.addEventListener("click", function (e) {
            e.preventDefault();
            $.ajax({
                url: '/songs/' + obj.value,
                type: 'DELETE',
                success: function (result) {
                    window.location.reload();
                }
            });
        });
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

/* PLAYER */
function createNoteCircles(intervals, colors) {
    var at = $('#alphaTab');
    console.log(intervals);
    at.on('alphaTab.playerReady', function () {
        getFretElements().each(function (i, text) {
            let x = text.x.baseVal[0].value;
            let y = text.y.baseVal[0].value;
            let circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            let $circle = $(circle).attr({
                cx: x + (text.innerHTML.length / 2 + 1) * 3,
                cy: y,
                r: 8,
                opacity: 0.4,
                stroke: "black",
                "stroke-width": 1,
                display: "none"
            });
            $(text).after($circle);
        });
        showNoteCircles(intervals, colors);
    });
}

function getFretElements() {
    texts = $("text[dominant-baseline='middle']");
    return texts;
}

function showNoteCircles(intervals, colors) {
    $("circle").each(function (i, circle) {
        if (colors[intervals[i]]) {
            $(circle).css({display: "block", fill: colors[intervals[i]]});
            console.log(circle);
        } else {
            $(circle).css({display: "none"});
        }
    });
}