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
        const file = $("#uploadTab")[0].files[0];
        uploadTab(file, tracks, $('#songTitle').val(), $('#songArtist').val());
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

function uploadTab(file, tracks, title, artist) {
    var fd = new FormData();
    fd.append("tab", file);
    fd.append("tracks", JSON.stringify(tracks));
    fd.append("title", title);
    fd.append("artist", artist);
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
                $container.empty();
                for (let [key, value] of Object.entries(response['tracks'])) {
                    $container
                        .append($('<label />').html(value))
                        .append($('<input/>').attr({type: 'checkbox', value: key, class: 'track-checkbox'}))
                        .append('<br />');
                }
                $('#uploadPlaceholder').innerText = '';
                $('#songInfo').show();
                $('#songTitle').val(response['title']);
                $('#songArtist').val(response['artist']);

            }
        },
        error: function (jqXHR, textStatus, errorMessage) {
            console.log(errorMessage); // Optional
        }
    });
}

/* PLAYER */

/* track information */

function editTrackInformation(tracks) {
    $('.btn-group').each(function (i, div) {
        let btn = $('<btn>').attr({
            class: "btn btn-default",
            type: "btn"
        });
        if (tracks[i]) {
            // TODO request analysis with a particular key here
            btn.text("Show Analysis");
            btn.click(function () {
                $.ajax({
                    url: 'tracks/' + tracks[i],
                    type: 'get',
                    success: function (response) {
                        createNoteCircles(response["intervals"]);
                        findMeasures(response["measureInfo"]);
                        btn.text("Show Analysis")
                    }
                });
                btn.text("Processing..");
            });
        } else {
            btn.text("Request Analysis")
            // todo request analysis to server
        }
        $(div).append(btn);
    });
}

/* Note circles */

function createNoteCircles(intervals) {
    getFretElements().each(function (i, text) {
        let x = text.x.baseVal[0].value;
        let y = text.y.baseVal[0].value;
        let circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        console.log(text, intervals[i]);
        let $circle = $(circle).attr({
            cx: x + (text.innerHTML.length / 2 + 1) * 3,
            cy: y,
            r: 8,
            class: "note note-" + (intervals[i] ? intervals[i].toString() : 'x') ,
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

const FORM_BAR_HEIGHT = 12;
const FORM_SHAPE_WIDTH = 150;
const FORM_SHAPE_HEIGHT = 175;

function findMeasures(measureInfo) {
    let measureId = 0;
    let matchId = 0;  // Used as a progressive number to show / hide form images popups
    let formIdMap = {};  // Maps each formId to an incremental index
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
            if (measureInfo[measureId]) {
                let j = 0;
                let matchesLength = (Object.keys(measureInfo[measureId]).length);
                let rectLen = width / matchesLength;
                let imageX = Number(x) + width / 2 - FORM_SHAPE_WIDTH / 2;
                $.each(measureInfo[measureId], function (formMeasureId, pngBytes) {
                    let position = Number(x) + j * rectLen;
                    let formId = formMeasureId.slice(0, formMeasureId.indexOf('_'));
                    if (!formIdMap[formId]) {
                        formIdMap[formId] = Object.keys(formIdMap).length;
                    }
                    drawRectangle(highEStringRect, position, y - 30, rectLen, FORM_BAR_HEIGHT, "form-bar form-bar-" + formIdMap[formId], matchId);
                    drawFormImage(highEStringRect, pngBytes, imageX, y - 35 - FORM_SHAPE_HEIGHT, matchId);
                    j++;
                    matchId++;
                })
            }
            measureId++;
        });
    });
}

function drawRectangle(nextElement, x, y, width, height, clsName, formId = null) {
    let rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect = $(rect).attr({
        x: x,
        y: y,
        width: width,
        height: height,
        class: clsName
    });
    $(nextElement).before(rect);
    if (formId != null) {
        $(rect).hover(function () {
            $("#form-img-" + formId).removeAttr("display");
            $(rect).attr("style", "opacity: 0.8");

        }, function () {
            $("#form-img-" + formId).attr("display", "none");
            $(rect).removeAttr("style");
        });
    }
}

function drawFormImage(nextElement, pngBytes, x, y, index) {
    let g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g = $(g).attr({
        id: "form-img-" + index,
        display: "none"
    });
    let img = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    img = $(img).attr({
        x: x,
        y: y,
        width: FORM_SHAPE_WIDTH,
        height: FORM_SHAPE_HEIGHT,
        href: "data:image/png;base64," + pngBytes,
        class: "form-image"
    });
    $(nextElement).before(g);
    $(g).append(img);
    drawRectangle(img, x, y, FORM_SHAPE_WIDTH, FORM_SHAPE_HEIGHT, "form-img-border");
}