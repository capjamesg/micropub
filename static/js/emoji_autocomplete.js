var char_count = 0;
var last_char = null;
var xhr = new XMLHttpRequest();

xhr.open('GET', '/emojis.json');

xhr.send();
    var emoji_names = [];
    var emojis = [];

xhr.onload = function() {
    if (xhr.status === 200) {
        emoji_req = JSON.parse(xhr.responseText);
        // split json into two lists
        for (var i in emoji_req) {
            emojis.push(i);
            emoji_names.push(emoji_req[i].toLowerCase().replace(" ", "_"));
        }
    }
};

var input = document.getElementById("content");
var character_count_element = document.getElementById("character_count");

input.onkeydown = function(e) {
    character_count_element.innerHTML = input.value.length;

    if (e.keyCode == 16) {
        last_char = e.keyCode;
    } else if (e.keyCode == 221) {
        last_char = e.keyCode;
    }

    if (last_char == 16) {
        var possible_emojis = document.getElementById("possible_emojis");
        var last_index = input.value.lastIndexOf(":");
        // get substring from last index to end
        var user_input_emoji_name = input.value.substring(input.value.lastIndexOf(":") + 1, input.value.length);

        if (user_input_emoji_name.length + 1 > 3) {
            var valid_emojis_to_show = emoji_names.map(function(emoji_name) {
                if (emoji_name.startsWith(user_input_emoji_name)) {
                    return emoji_name + " (" + emojis[emoji_names.indexOf(emoji_name)] + ")"
                }
            });

            valid_emojis_to_show = valid_emojis_to_show.filter(item => item != undefined);

            possible_emojis.innerHTML = "<h3>Suggested Emojis</h3>";

            for (var i in valid_emojis_to_show) {
                possible_emojis.innerHTML += "<p>" + valid_emojis_to_show[i] + "</p>";
            }
        }
        
        if (e.keyCode == 32) {
            // if value in emoji
            // get last index of :
            var last_index = input.value.lastIndexOf(":");
            // get substring from last index to end
            var user_emoji_name = input.value.substring(last_index + 1);
            
            var valid_emojis_to_show = emoji_names.map(function(emoji_name, index) {
                if (emoji_name.startsWith(user_emoji_name)) {
                    return emojis[index];
                }
            });

            valid_emojis_to_show = valid_emojis_to_show.filter(item => item != undefined);

            var exact_match = valid_emojis_to_show.filter(item => item == user_emoji_name);

            console.log(exact_match);

            if (exact_match.length == 1) {
                input.value = input.value += exact_match[0];
                input.value = input.value.replace(":" + exact_match, "");
                var possible_emojis = document.getElementById("possible_emojis");
                possible_emojis.innerHTML = "";
            }
            
            if (valid_emojis_to_show.length > 0) {
                input.value = input.value += valid_emojis_to_show[0];
                input.value = input.value.replace(":" + user_emoji_name, "");
                var possible_emojis = document.getElementById("possible_emojis");
                possible_emojis.innerHTML = "";
            }
        }
    } else if (last_char == 221) {
        var last_index = input.value.lastIndexOf("[]");
        // get substring from last index to end
        var link = input.value.substring(last_index + 2, input.value.length);

        if (e.keyCode == 32) {
            input.value = input.value.replace("[]" + link, "<a href='https://" + link + "'>" + link + "</a>");
        }
    } else if (last_char == 32) {
        last_char = null;
    }
}

function add_emoji(emoji) {
    var url = document.getElementById("in-reply-to").value;
    if (emoji == "🪀") {
        emoji = "<a href='" + url + "' class='u-yo-of'>Yo! 🪀</a>"
    } else if (emoji == "👉") {
        emoji = "<a href='" + url + "' class='u-poke-of'>Poke 👉</a>"
    }
    char_count++;
    input.value += emoji;
}