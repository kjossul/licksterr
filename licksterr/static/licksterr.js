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

/* Note circles */

function createNoteCircles(intervals) {
    getFretElements().each(function (i, text) {
        let x = text.x.baseVal[0].value;
        let y = text.y.baseVal[0].value;
        let circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        let $circle = $(circle).attr({
            cx: x + (text.innerHTML.length / 2 + 1) * 3,
            cy: y,
            r: 8,
            class: "note note-" + intervals[i].toString(),
        });
        $(text).after($circle);
    });
}

function getFretElements() {
    texts = $("text[dominant-baseline='middle']");
    return texts;
}

function updateNoteColors(colors) {
    colors.forEach(function (color, i) {
        className = ".note-" + i;
        classContainer = $("head").find('style[data-class="' + className + '"]');
        if (color) {
            classContainer.html(className + ' {' +
                'fill:' + color + '; display:block' +
                '}');
        } else {
            classContainer.html(className + ' {display:none}');
        }
    });
}

/* Form shape information */

function findMeasures(measureInfo, imgDir) {
    $("svg").slice(1).each(function (i, svg) {
        let start = null;
        let xs = {};
        let highEStringRect = null;
        let y = null;
        $(svg).find("rect").each(function (j, rect) {
            let x = rect.x.baseVal.value;
            start = start ? start : x;
            if (j > 6 && start === x) {
                // We have examined all pentagram, no need to go on with the tab, because we already know measures
                // positions and lengths. Exit loop and keep only the y offset of the tablature.
                highEStringRect = rect;
                y = rect.y.baseVal.value;
                return false;
            }
            let width = rect.width.baseVal.value;
            if (width > 20) {
                xs[x] = width;
            }
        });
        $.each(xs, function (x, width) {
            if (!measureInfo[i]) {
                // No measure was matched here, probably just a whole pause
                drawRectangle(highEStringRect, x, y - 30, width, 10)
            } else {
                let j = 0;
                let rectLen = width / (Object.keys(measureInfo[i]).length);
                $.each(measureInfo[i], function (measureId, match) {
                    drawRectangle(highEStringRect, x + j * rectLen, y - 30, rectLen, 10);
                    let link = imgDir + "/" + measureId + '.svg';
                    drawFormImage(highEStringRect, link, x + j * rectLen, y - 60);
                    j += 1;
                })
            }
        });
    });
}

function drawRectangle(nextElement, x, y, width, height) {
    let rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    let $rect = $(rect).attr({
        x: x,
        y: y,
        width: width,
        height: height,
        class: "form-bar form-bar-"
    });
    $(nextElement).before($rect);
}

function drawFormImage(nextElement, link, x, y) {
    let img = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    let $img = $(img).attr({
        x: x,
        y: y,
        width: 300,
        height: 300,
        href: link
    });
    $(nextElement).before($img);
}