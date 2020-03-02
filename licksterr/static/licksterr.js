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
    $('.title').each(function (i, div) {
        if (tracks[i])
            $(div).append('<span>★</span>');
        $(div).click(function () {
            $("#alphaTab").on("alphaTab.rendered", function () {
                if (tracks[i]) {
                    initSongInfoContainer("Contacting server..");
                    // todo remove click listener on track element otherwise things get messy
                    $.ajax({
                        url: 'tracks/' + tracks[i],
                        type: 'get',
                        success: function (response) {
                            let d = response;
                            let text = "Key of " + d['key'] + " " + (d['isMajor'] ? 'major' : 'minor') + " (" +
                                d["scale"]["name"].toLowerCase() + " mode)";
                            initSongInfoContainer(text);
                            findMeasures(response["tuning"], response["scale"]['key']);
                        }
                    });
                } else {
                    initSongInfoContainer("Choose a ★ track for analysis.");
                }
            })
        });
    });
}

function initSongInfoContainer(innerText) {
    let header = $("svg")[0];
    let $trackInfo = $('#trackInfo');
    if (!$trackInfo.length) {
        $trackInfo = document.createElementNS("http://www.w3.org/2000/svg", "text");
        $($trackInfo).attr({
            id: 'trackInfo',
            y: header.height.baseVal.value - 60,
            x: header.width.baseVal.value - 260,
            style: "stroke: none; font:15px 'Georgia'",
            dominantBaseline: 'hanging'
        });
        header.append($trackInfo);
    }
    $($trackInfo).html(innerText);
}

/* Note circles */

function createNoteCircles(texts, stringHeights, tuning, key) {
    texts.each(function (i, text) {
        let x = text.x.baseVal[0].value;
        let y = text.y.baseVal[0].value;
        let circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        let string = stringHeights.indexOf(y);
        let fret = $(text).html().replace(/[^0-9]+/g, '');
        let interval = fret ? Math.abs(((tuning[string] + Number(fret)) % 12 - key)) % 12 : -1;
        let $circle = $(circle).attr({
            cx: x + (text.innerHTML.length / 2 + 1) * 3,
            cy: y - 1,
            r: 8,
            class: "note note-" + interval,
        });
        $(text).after($circle);
    });
}

function updateNoteColors(colors) {
    colors.forEach(function (color, i) {
        className = ".note-" + i;
        classContainer = $("head").find('style[data-class="' + className + '"]');
        if (color) {
            classContainer.html(className + ' {fill:' + color + '; display:block}');
        } else {
            classContainer.html(className + ' {display:none}');
        }
    });
}


function findMeasures(tuning, key) {
    $("svg").slice(1).each(function (i, svg) {
        let heights = new Set();
        let marker = $(svg).find(".at").last();
        marker.nextAll("rect").slice(0, -2).each(function (j, rect) {
            heights.add(rect.y.baseVal.value);
        });
        heights = Array.from(heights);
        let texts = $(svg).find("text[dominant-baseline='middle']");
        createNoteCircles(texts, heights, tuning, key);
    });
}
