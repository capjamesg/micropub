import re

def get_rendered_html(string, lang):
    string = string.replace("</p>", "")
    final_string = ""

    if lang == "python":
        to_look = ["def", "as", "with ", "open", " = ", "if", " in ", "elif", "import", "except", "try", "print", "return"]
        colors = ["blue", "blue", "blue", "orange", "pink", "orange", "orange", "orange", "orange", "orange", "orange", "orange", "orange", "purple", "purple"]
    elif lang == "bash":
        to_look = ["for", "in", "done", "do", "((", "))", "echo", "if", "else"]
        colors = ["purple", "purple", "purple", "purple", "green", "green", "orange", "purple", "purple"]
    else:
        return string

    finding = False

    string_chars = ['"', "'", "`"]

    for i in string.split("\n"):
        if finding == True:
            if "#" in i:
                i = "<span style='color:red'># " + i + "</span>"
                final_string += "<p>" + i + "</p>"
                continue
            
            for c in string_chars:
                if c in i:
                # get all text in quotes with regex
                    quote_regex = re.compile(r'{}(.*?){}'.format(c, c))

                    # get all text in quotes
                    quote_text = quote_regex.findall(i)

                    for item in quote_text:
                        if len(item) > 0:
                            i = i.replace(c + item + c, "<span style='color: green'>" + c + item + c + "</span>")

            for item in range(0, len(to_look)):
                if to_look[item] in i.strip():
                    i = i.replace(to_look[item], f"<span style='color:{colors[item]}'>{to_look[item]}</span>")

            if i.strip().startswith("for "):
                i = i.replace("for", "<span style='color:orange'>for</span>")
            if i.strip().startswith("while "):
                i = i.replace("while", "<span style='color:orange'>while</span>")
            if i.strip().startswith("else:"):
                i = i.replace("else:", "<span style='color:orange'>else</span>:")
            if i.strip().startswith("fi"):
                i = i.replace("else:", "<span style='color:purple'>fi</span>")
            
            final_str = []

            for w in i.split(" "):
                if w.startswith("$"):
                    w = f"<span style='color:darkblue'>{w}</span>"
                    final_str.append(w)
                else:
                    final_str.append(w)

            i = " ".join(final_str)

            final_string += "<p>" + i + "</p>"

        if "<pre" in i:
            finding = True
        if "</pre>" in i:
            finding = "no"

        if finding == "no":
            break

    return "<pre>" + final_string + "</pre>"