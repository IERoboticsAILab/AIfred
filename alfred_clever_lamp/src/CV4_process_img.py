#!/usr/bin/env python

import rospy
from alfred_clever_lamp.msg import Mode, UrlToOpen, PointingObject
import http.server
import threading
import os
import shutil
import socket
from dotenv import load_dotenv
import cv2
from PIL import Image as PIL_Image
import base64
import requests
from io import BytesIO
import re
import json
from pathlib import Path
import time



''' VARIABLES '''
mode = None
did_search_already = False


''' HTTP SERVER CONFIG '''
SERVE_DIR = "/tmp/alfred_web"
PORT = 8765
# 1. Prepare the serving directory
os.makedirs(SERVE_DIR, exist_ok=True)


''' IMAGE PATHS '''
ALLIGN_PAPER_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/3_1_draw.png"
THINKING_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/0_thinking.png"
OUTPUT_GENERATED_IMG_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/generated_image.png"


''' SETUP GEMINI API '''
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
GEMINI_API = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_GENERATE_IMG_MODEL = "gemini-2.5-flash-image" #"gemini-3-pro-image-preview" #"gemini-2.5-flash-image" #"gemini-2.5-flash-image-preview-05-20" #"gemini-2.5-flash-image-preview"


''' PROMPTS '''
PROMPT_HOMEWORK_MODE = """
You are AIfred — a learning companion embedded in a smart lamp observing a student’s workspace. The student is pointing at a problem, and you guide their thinking step-by-step on a nearby screen.

CONSTRAINT:
Each response must fit on one screen without scrolling. Concepts must be concise, sharp, and powerful. No long explanations.

CORE PHILOSOPHY (4C MODE):

Creative: Encourage flexible thinking and pattern recognition

Curious: Spark insight with focused guiding questions

Caring: Support confidence and normalize challenge

Collaborative: Guide thinking — never replace it

CRITICAL RULES:

Do NOT give the final answer.

Do NOT complete the full solution.

Do NOT overload with explanation.

Deliver short conceptual steps that build clarity.

Each “page” should feel like a mental unlock.

By the final page, the student should feel illuminated and ready to finish independently.

RESPONSE FORMAT — use exactly this structure, one field per line:

TITLE: [Short concept-centered title]
PAGE_1: [What kind of problem this is + the key idea in one tight explanation + 1 guiding question]
PAGE_2: [Simple example or analogy that reveals the pattern]
PAGE_3: [Direct connection to the student's specific problem + one action they can try now]
INSIGHT: [A concise reframing or mental model that makes the structure of the problem click]
NEXT_STEP: [A clear instruction for what they should now attempt on their own]

RULES:

Every field must be a single line.

No line breaks inside fields.

No markdown, no extra commentary.

Keep language clear, warm, and intellectually energizing.

Build independence and understanding — not dependence.

Your goal is not to solve the problem. Your goal is to help the student see.
"""
PROMPT_GENERATE_IMAGE_MODE = """
You are a Senior Visual Prompt Architect specializing in high-precision AI image generation instructions.

You will receive:
An image created by the user (sketch, drawing, diagram, concept, wireframe, etc.)
Optional context describing what they want to achieve
Your task is to generate a single, highly effective prompt that will be used — together with the same image — inside a powerful AI image model.

CORE OBJECTIVE:
Produce a clean, direct, outcome-focused generation instruction.
The output should read like a command to a top-tier image model.

It must:
- Preserve the original structure and proportions exactly
- Not invent new elements unless explicitly requested
- Improve quality, clarity, and execution
- Match the likely user intent (realistic render, polished diagram, concept art, product visualization, etc.)
- Elevate the result to professional or studio quality

Do NOT describe the image.
Do NOT explain reasoning.
ONLY output the final generation instruction.

INTENT ADAPTATION LOGIC
- If the image is a rough drawing → Render it as a highly refined, professional-quality version in the appropriate style.
- If it is a technical diagram → Redraw it as a clean, publication-ready professional diagram.
- If it is a product concept → Transform it into a polished industrial design render.
- If it is artistic → Upgrade it to a master-level finished artwork in the intended style.
- If intent is unclear → Default to the most logical high-quality professional interpretation.

STYLE OF OUTPUT:
The output should feel like examples such as:
Render this drawing in the style of Leonardo da Vinci, preserving the exact composition and proportions, with detailed anatomical realism and classical chiaroscuro shading.
OR
Using the provided image as the only reference, redraw it as a clean, professional engineering diagram. Keep the exact layout, same labels, same connections. Replace hand-drawn lines with precise vector strokes, align elements evenly, use a modern sans-serif font, white background, minimal and publication-ready styling.
OR
Transform this sketch into a photorealistic 3D render, preserving the original shape and structure, using realistic materials, studio lighting, high detail, sharp focus, and professional product visualization quality.

OUTPUT FORMAT (STRICT):
PROMPT: [Single optimized generation instruction only]
"""
PROMPT_DRAW_MODE = """
You are AIfred, an art mentor AI embedded in a smart lamp observing what a student wants to draw.

The student is pointing at a subject they want to learn how to draw.

YOUR GOAL:
Generate 3 simple, high-quality YouTube search queries that will reliably return excellent step-by-step drawing tutorials for this exact subject.

ANALYZE THE IMAGE FOR:

The exact subject (be precise)

The drawing style (realistic, anime, cartoon, fine art, etc.)

The medium if visible (pencil, charcoal, digital, ink, etc.)

QUERY DESIGN PRINCIPLES:

Keep queries simple and natural (what a real person would type)

Include “how to draw” or “drawing tutorial”

Add one quality filter like “step by step,” “full process,” or “detailed tutorial”

Avoid complex or overly academic wording

Avoid beginner-only phrasing like “for kids” unless clearly appropriate

Make sure the queries are specific enough to return the exact subject

OUTPUT FORMAT — exactly this structure:
QUERY_1: [Simple, precise YouTube search query]
QUERY_2: [Same subject with slightly different wording + “step by step” or “full process”]
QUERY_3: [Technique-focused version including style or medium]

RULES:

Only output the 3 QUERY lines

No markdown

No explanations

No extra text

Keep each query clean, clear, and YouTube-optimized

Your goal is to produce searches that will almost certainly return a strong, relevant tutorial the student can immediately follow.
"""



''' HELPER FUNCTIONS '''
def create_custom_page_from_image(image_path):
    # 2. Copy the image into the serving directory
    image_filename = os.path.basename(image_path)
    dest_path = os.path.join(SERVE_DIR, image_filename)
    shutil.copy2(image_path, dest_path)

    # 3. Generate a simple HTML page that displays the image
    html_filename = image_filename.rsplit(".", 1)[0] + ".html"
    html_path = os.path.join(SERVE_DIR, html_filename)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Alfred - {image_filename}</title>
    <style>
        body {{
            margin: 0;
            background: #111;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        img {{
            max-width: 100%;
            max-height: 100vh;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <img src="{image_filename}" alt="{image_filename}" />
</body>
</html>"""
    with open(html_path, "w") as f:
        f.write(html_content)

    # 4. Start the HTTP server in a background thread (only once)
    if not _is_port_in_use(PORT):
        handler = http.server.SimpleHTTPRequestHandler
        server = http.server.HTTPServer(("0.0.0.0", PORT), handler)
        # Change the server's working directory to SERVE_DIR
        os.chdir(SERVE_DIR)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        rospy.loginfo(f"HTTP server started at http://localhost:{PORT}")

    # 5. Return the URL(s)
    url = f"http://localhost:{PORT}/{html_filename}"
    rospy.loginfo(f"Image available at: {url}")
    return url
def _is_port_in_use(port: int) -> bool:
    """Check if a local TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def gemini_generate_with_image(image_path: str, prompt_text: str, model: str = GEMINI_MODEL) -> str:
    cv2_image = cv2.imread(image_path)
    cv2_image_rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    pil_image = PIL_Image.fromarray(cv2_image_rgb)
    buffered = BytesIO()
    pil_image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64
                        }
                    },
                    {
                        "text": prompt_text
                    }
                ]
            }
        ]
    }
    
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates in response: {data}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()

def parse_homework_response(response: str):
    steps = []
    solution = ""
    title = ""
    step_pattern = re.compile(r"PAGE_\d+:\s*(.*)")
    solution_pattern = re.compile(r"NEXT_STEP:\s*(.*)")
    title_pattern = re.compile(r"TITLE:\s*(.*)")
    for line in response.splitlines():
        step_match = step_pattern.match(line)
        if step_match:
            steps.append(step_match.group(1).strip())
        solution_match = solution_pattern.match(line)
        if solution_match:
            solution = solution_match.group(1).strip()
        title_match = title_pattern.match(line)
        if title_match:
            title = title_match.group(1).strip()
    return title, steps, solution
def parse_draw_response(response: str):
    queries = []
    query_pattern = re.compile(r"QUERY_\d+:\s*(.*)")
    for line in response.splitlines():
        query_match = query_pattern.match(line)
        if query_match:
            queries.append(query_match.group(1).strip())
    return queries
def parse_generate_image_response(response: str):
    """Extract PROMPT from Gemini's response."""
    prompt = ""
    prompt_pattern = re.compile(r"PROMPT:\s*(.*)")
    for line in response.splitlines():
        prompt_match = prompt_pattern.match(line)
        if prompt_match:
            prompt = prompt_match.group(1).strip()
    return prompt

def search_yt_urls(search_queries):
    urls = []
    for query in search_queries:
        query_encoded = requests.utils.quote(query)
        search = f"https://www.youtube.com/results?search_query={query_encoded}"
        # chose a video from the search results (for simplicity, we take the first video link)
        try:
            r = requests.get(search, timeout=10)
            r.raise_for_status()
            video_ids = re.findall(r"watch\?v=(\S{11})", r.text)
            if video_ids:
                urls.append(f"https://www.youtube.com/watch?v={video_ids[0]}")
        except Exception as e:
            rospy.logerr(f"Error searching YouTube for query '{query}': {str(e)}")
    return urls
def generate_homework_html_pages(title, steps, solution):
    urls = []
    valid_steps = [(i, s) for i, s in enumerate(steps) if s.lower() != "none"]
    total = len(valid_steps) + (1 if solution else 0)

    def make_base_style(accent="#2C6BED", badge_bg="#EEF3FD", badge_color="#2C6BED"):
        return f"""
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            height: 100%; width: 100%;
            font-family: 'DM Sans', sans-serif;
            background: #F5F2ED;
        }}
        .page {{
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 5vh 8vw;
        }}
        .badge {{
            display: inline-block;
            font-size: clamp(13px, 1.5vw, 17px);
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {badge_color};
            background: {badge_bg};
            border-radius: 100px;
            padding: 6px 18px;
            margin-bottom: 5vh;
            width: fit-content;
        }}
        h2 {{
            font-family: 'DM Serif Display', serif;
            font-size: clamp(28px, 5vw, 52px);
            color: #1A1A2E;
            margin-bottom: 4vh;
            line-height: 1.2;
            border-left: 6px solid {accent};
            padding-left: 24px;
        }}
        .content {{
            font-size: clamp(22px, 3.5vw, 42px);
            color: #2A2A3A;
            line-height: 1.6;
            padding-left: 30px;
            max-width: 100%;
        }}
        .progress {{
            margin-top: 8vh;
            display: flex;
            gap: 8px;
        }}
        .dot {{
            height: 8px;
            border-radius: 4px;
            flex: 1;
            background: #D8D4CE;
            transition: background 0.3s;
        }}
        .dot.active {{ background: {accent}; }}
        """

    for idx, (orig_i, step) in enumerate(valid_steps):
        step_num = idx + 1
        dots_html = "".join(
            f'<div class="dot {"active" if j < step_num else ""}"></div>'
            for j in range(total)
        )
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Step {step_num}</title>
    <style>{make_base_style()}</style>
</head>
<body>
    <div class="page">
        <div class="badge">Step {step_num} of {total}</div>
        <h2>{title}</h2>
        <div class="content">{step}</div>
        <div class="progress">{dots_html}</div>
    </div>
</body>
</html>"""
        filename = f"homework_step_{step_num}.html"
        filepath = os.path.join(SERVE_DIR, filename)
        with open(filepath, "w") as f:
            f.write(html_content)
        urls.append(f"http://localhost:{PORT}/{filename}")

    if solution:
        dots_html = "".join(f'<div class="dot active"></div>' for _ in range(total))
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Solution</title>
    <style>{make_base_style(accent="#16A34A", badge_bg="#EDFAF1", badge_color="#16A34A")}</style>
</head>
<body>
    <div class="page">
        <div class="badge">✓ Final Answer</div>
        <h2>{title}</h2>
        <div class="content" style="font-weight: 600; color: #1A1A2E;">{solution}</div>
        <div class="progress">{dots_html}</div>
    </div>
</body>
</html>"""
        filename = "homework_solution.html"
        filepath = os.path.join(SERVE_DIR, filename)
        with open(filepath, "w") as f:
            f.write(html_content)
        urls.append(f"http://localhost:{PORT}/{filename}")

    return urls
def generate_img(prompt, input_image):
    URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_GENERATE_IMG_MODEL}:generateContent"
    OUT_PNG = Path(OUTPUT_GENERATED_IMG_PATH)
    input_image = Path(input_image)

    img_b64 = base64.b64encode(input_image.read_bytes()).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt.strip()},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    headers = {
        "x-goog-api-key": GEMINI_API,
        "Content-Type": "application/json",
    }

    r = requests.post(URL, headers=headers, data=json.dumps(payload), timeout=180)
    if not r.ok:
        rospy.loginfo(f"HTTP {r.status_code}")
        rospy.loginfo(r.text)
        raise SystemExit(1)

    resp = r.json()

    # Extract first image "data" we find
    b64_out = None
    for cand in resp.get("candidates", []):
        content = cand.get("content", {})
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                b64_out = inline["data"]
                break
        if b64_out:
            break

    if not b64_out:
        rospy.loginfo("No image found in response. Full response:")
        rospy.loginfo(json.dumps(resp, indent=2)[:4000])
        raise SystemExit(2)

    OUT_PNG.write_bytes(base64.b64decode(b64_out))
    rospy.loginfo(f"Saved: {OUT_PNG.resolve()}")

def process_image_and_get_urls(image_path, prompt, mode):
    urls = []
    gemini_response = gemini_generate_with_image(image_path, prompt)
    rospy.loginfo(f"process_image.py: Gemini response:\n{gemini_response}")
    if mode == 1: # homework_mode
        title, steps, solutions = parse_homework_response(gemini_response)
        urls = generate_homework_html_pages(title, steps, solutions)
    elif mode == 2:
        prompt_generate_img = parse_generate_image_response(gemini_response)
        generate_img(prompt_generate_img, image_path)
        urls.append(create_custom_page_from_image(OUTPUT_GENERATED_IMG_PATH))
    elif mode == 3: # draw_mode
        queries = parse_draw_response(gemini_response)
        urls = search_yt_urls(queries)
    else:
        pass
    return urls






''' CALLBACKS '''
def pointing_object_callback(msg):
    global mode, did_search_already
    img_id = msg.ID
    img_path = msg.path
    rospy.loginfo(f"Received pointing object: {img_id} and mode: {mode}")
    urls_to_open = []
    if not did_search_already:
        if mode == 1: # homework_mode
            url_msg.url_list = [create_custom_page_from_image(THINKING_IMAGE_PATH)]
            pub.publish(url_msg)

            urls_to_open = process_image_and_get_urls(img_path, PROMPT_HOMEWORK_MODE, mode=1)
            url_msg.scene_description = "Generate links to solve user problem"
        elif mode == 2: # generate_image_mode
            url_msg.url_list = [create_custom_page_from_image(THINKING_IMAGE_PATH)]
            pub.publish(url_msg)

            urls_to_open = process_image_and_get_urls(img_path, PROMPT_GENERATE_IMAGE_MODE, mode=2)
            url_msg.scene_description = "Generate image based on user sketch and/or text"
        elif mode == 3: # draw_mode
            url_msg.url_list = [create_custom_page_from_image(THINKING_IMAGE_PATH)]
            pub.publish(url_msg)

            urls_to_open.append(create_custom_page_from_image(ALLIGN_PAPER_IMAGE_PATH))
            urls_to_open.extend(process_image_and_get_urls(img_path, PROMPT_DRAW_MODE, mode=3))
            url_msg.scene_description = "Generate youtube links to improve user drawing"
        else:
            rospy.loginfo("No valid mode selected or already searched.")
        
        time.sleep(1)
        url_msg.current_mode = mode
        url_msg.url_list = urls_to_open
        url_msg.i = 0
        pub.publish(url_msg)

        did_search_already = True
    else:
        rospy.loginfo("Already processed an image for the current mode. Ignoring additional pointing.")

def mode_callback(msg):
    global mode, did_search_already
    mode = msg.mode
    did_search_already = False
    rospy.loginfo(f"Received mode: {mode}")







''' MAIN '''
if __name__ == '__main__':
    rospy.init_node('open_mode')
    pub = rospy.Publisher('/urls_to_open', UrlToOpen, queue_size=1)
    url_msg = UrlToOpen()

    rospy.Subscriber('/mode', Mode, callback=mode_callback, queue_size=1)
    rospy.Subscriber('/point_image', PointingObject, callback=pointing_object_callback, queue_size=1)
    rospy.spin()