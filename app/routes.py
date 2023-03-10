from app import app
from flask import render_template, request, flash, redirect, url_for
import openai
from transformers import GPT2Tokenizer
import os


# with open("OPENAI_API_KEY.txt", "r") as k:
#    openai.api_key = k.readline()
#    k.close()
openai.api_key = os.environ["OPENAI_API_KEY"]


tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
default_headings = "AP, TIP, NOTE, AP®, Continuity and Change, Analyzing Evidence, Causation, Comparison, Contextualization, image pop up, Map"
default_length = "long"
punctuation = [".", "!", "?"]
notes = ""
input = ""

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if request.form["post_type"] == "submit_text":
            notes = ""
            extra_notes = ""
            in_extra = False
            raw_notes = []

            input = request.form["text_in"]
            extra_markers = request.form["submit_headings"].split(", ")
            note_length = request.form["submit_length"]
            lines = [line.strip() for line in input.split("\n") if len(line) > 1]
            
            for curline in lines:
                not_sentence = curline[-1] not in punctuation
                is_short = len(curline.split()) < 10
                caps = [word[0].isupper() for word in curline.split()]
                is_heading = caps.count(True)/len(caps) > 0.5
                extra = any([marker in curline for marker in extra_markers])

                if not_sentence and is_short and is_heading:
                    if extra:
                        extra_notes += f'• {curline.strip(". ")}\n'
                        in_extra = True
                    else:
                        raw_notes.append([curline, ""])
                        in_extra = False
                else:
                    if in_extra:
                        extra_notes += f'        • {curline.strip(". ")}\n'
                        in_extra = False
                    else:
                        if len(raw_notes) == 0:
                            raw_notes.append([curline, ""])
                        else:
                            raw_notes[-1][1] += f"{curline}\n"

            for topic in range(len(raw_notes)):
                notes += f"\n• {raw_notes[topic][0]}\n"

                prompt = f'Summarize the following text: "{raw_notes[topic][1]}"'
                number_of_tokens = len(tokenizer(prompt)['input_ids'])
                print(number_of_tokens)
                if number_of_tokens > 4000:
                    flash(f"Paragraph:\n\n\"{raw_notes[topic][1]}\"\n\nexceeds ~3000 word limit. Consider consolidating or splitting this piece of text.", "danger")
                    break

                try:
                    if note_length == "short":
                        max_tokens = (4096-number_of_tokens)//3
                    elif note_length == "medium":
                        max_tokens = (4096-number_of_tokens)//3*2
                    else:
                        max_tokens = 4096-number_of_tokens

                    completion = openai.Completion.create(engine="text-davinci-003", max_tokens=max_tokens, prompt=prompt)
                except openai.error.ServiceUnavailableError:
                    flash("OpenAI servers are currently overloaded or not ready yet. Please try again shortly.", "danger")
                    break
                except openai.error.RateLimitError:
                    flash("Text length hit OpenAI's rate limit, consider reprocessing your text in chunks.", "danger")
                    break

                for point in completion.choices[0].text.strip("\n. ").split(". "):
                    notes += f"        • {point}\n"

            notes += "\n\nExtras:\n" + extra_notes
            notes = notes.strip('" ')

            return render_template("home.html.j2", input=input, output=notes, headings=", ".join(extra_markers), length=note_length)
        elif request.form["post_type"] == "submit_settings":
            input = request.form["settings_input"]
            notes = request.form["settings_output"]
            extra_markers = request.form["headings"]
            note_length = request.form["note_length"]

            return render_template("home.html.j2", input=input, output=notes, headings=extra_markers, length=note_length)
    else:
       return render_template("home.html.j2", input="", output="", headings=default_headings, length=default_length)

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html.j2")
