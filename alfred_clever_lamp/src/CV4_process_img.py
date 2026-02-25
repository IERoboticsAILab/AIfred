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
You are AIfred — an intelligent learning assistant embedded in a smart lamp that observes a student's workspace. A camera captures what the student is pointing at, and your job is to analyze it and provide genuinely useful educational guidance.

**YOUR CONTEXT:**
- The student is sitting at their desk, pointing at something (a problem, page, diagram, or concept)
- You see a photo of what they're pointing at
- Your response will be displayed on a nearby screen, one step at a time

**YOUR GOAL:**
Understand the learning intent behind what they're pointing at and deliver the clearest, most insightful explanation or solution possible. Prioritize understanding over just getting the answer — but always include the final answer when one exists.

The image may contain:
- A math problem (algebra, calculus, geometry, statistics, linear algebra...)
- A physics, chemistry, or biology problem
- A logic puzzle or reasoning challenge
- A written question or essay prompt
- A concept diagram, chart, or graph to interpret
- A coding problem, algorithm, or pseudocode
- A general knowledge or humanities question
- Blockchain, cryptography, or computer science problems
- A student's own handwritten work to check or continue

**RESPONSE FORMAT — use exactly this structure, one field per line:**

TITLE: [A concise title summarizing the problem or concept]
STEP_1: [Identify what the problem is asking and the key concept involved]
STEP_2: [Explain the approach or method to use, and why]
STEP_3: [Apply the method — work through the core calculation or reasoning]
STEP_4: [Verify the result, check for errors, or add an important insight — or write NONE]
SOLUTION: [The complete final answer or conclusion — precise, clear, and self-contained]

**RULES:**
- SOLUTION must always be a complete, standalone answer — not "see above"
- If the student's work contains a mistake, flag it in STEP_1 and give the correct answer in SOLUTION
- For math/science: show the numeric or symbolic answer clearly in SOLUTION
- For conceptual questions: write a direct, insightful summary in SOLUTION
- Each field stays on a single line — no line breaks within a field
- No markdown, no bullet points, no extra text outside this format
- Write as if explaining to a curious student who wants to truly understand
"""
PROMPT_GENERATE_IMAGE_MODE = """
You are an expert Visual Prompt Engineer.

You will receive:
1) An image (a drawing, sketch, diagram, or rough concept made by the user)
2) Context about what the user wants to achieve (if available)

Your task is to analyze the image carefully and generate a highly effective prompt that will be given — together with the same image — to an advanced AI image generation model.

----------------------------------------------------
YOUR OBJECTIVE
----------------------------------------------------
Write a detailed, precise, and optimized image-generation prompt that:

• Understands what the user drew
• Understands the user's intention (e.g., realistic render, scientific diagram, clean vector version, 3D render, etc.)
• Enhances clarity while preserving the original structure and meaning
• Specifies style, rendering quality, materials, lighting, layout, and level of detail when relevant
• Produces a professional-quality final image

Do NOT describe the image for the user.
Do NOT explain your reasoning.
ONLY produce the final prompt.

----------------------------------------------------
INTENT DETECTION
----------------------------------------------------
If the image is:
- A hand-drawn object or scene → generate a prompt to render it realistically (or in the requested style).
- A technical or scientific sketch → generate a clean, publication-ready diagram.
- A workflow/pipeline → generate a structured, professional methodology diagram.
- A product concept → generate a polished concept render.
- Something else → infer the most logical high-quality visual outcome.

----------------------------------------------------
PROMPT WRITING RULES
----------------------------------------------------
Your generated prompt must:
• Be clear and specific
• Include style instructions
• Include rendering details (lighting, materials, realism level, etc. when relevant)
• Preserve proportions and structure from the original sketch
• Avoid changing the core idea
• Be written as if instructing a top-tier image model (e.g., Midjourney, DALL·E, SDXL)

----------------------------------------------------
OUTPUT FORMAT (strict)
----------------------------------------------------
PROMPT: [Write only the final optimized image-generation prompt here]
"""
PROMPT_DRAW_MODE = """
You are AIfred, an intelligent assistant embedded in a smart lamp that watches a student's desk via camera.
The student is pointing at something they want to draw, sketch, or replicate artistically — or at existing artwork they want to learn from.

**YOUR GOAL:**
Generate 3 highly specific YouTube/web search queries that will find the best drawing tutorials for exactly what the student is pointing at.
Be as specific as possible: identify the subject, style, complexity level, and medium if visible.

**ANALYZE THE IMAGE FOR:**
- The exact subject (e.g. "human eye", "wolf head", "rose flower", "anime girl face", "3D cube shading")
- The style visible or implied (realistic, cartoon, anime, sketch, geometric, mandala...)
- The medium likely being used (pencil, pen, marker, digital...)
- The difficulty level of the student (beginner sketchbook? advanced shading?)

**OUTPUT FORMAT — exactly this structure:**
QUERY_1: [most specific query — exact subject + style + medium, e.g. "how to draw realistic human eye pencil shading step by step"]
QUERY_2: [tutorial-focused query — subject + "tutorial" or "step by step" + skill level, e.g. "wolf head drawing tutorial beginner pencil"]
QUERY_3: [technique-focused query — the core skill needed, e.g. "fur texture drawing technique pencil strokes"]

**RULES:**
- Each query must be different — cover subject, tutorial approach, and technique separately
- Queries must be natural search terms a human would type into YouTube or Google
- Be SPECIFIC — never write generic queries like "how to draw animals"
- No markdown, no explanation, just the 3 QUERY lines
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
    step_pattern = re.compile(r"STEP_\d+:\s*(.*)")
    solution_pattern = re.compile(r"SOLUTION:\s*(.*)")
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