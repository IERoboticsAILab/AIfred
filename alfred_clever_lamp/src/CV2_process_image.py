#!/usr/bin/env python

import rospy
import os
from dotenv import load_dotenv
import cv2
from PIL import Image as PIL_Image
import base64
import requests
from io import BytesIO
import re
import json
from alfred_clever_lamp.msg import PointingObject, UrlToOpen
import tempfile


''' USEFUL VARIABLES '''
PROMPT = """You are an intelligent learning assistant. Analyze what the user is pointing at and understand their learning intent.

**YOUR GOAL:**
Provide the MOST USEFUL educational content based on:
- What they're pointing at
- The context (is it a problem to solve? something to learn? something to create?)
- Their implicit learning goal

**RESPONSE MODES:**

**MODE: MATH**
Use when user points at mathematical equations, formulas, calculations, or math problems that need solving.
```
MODE: MATH
TITLE: [2-4 word title]
STEP_1: [First step with clear explanation]
STEP_2: [Second step]  
STEP_3: [Third step]
SOLUTION_OR_FIX: [Final answer with units if applicable and/or fix mistakes if user made an error]
```

**MODE: CODE**
Use when user points at programming code, algorithms, syntax errors, or wants to understand code logic.
```
MODE: CODE
TITLE: [2-4 word title]
LANGUAGE: [Programming language]
EXPLANATION: [What the code does in 1-2 sentences]
KEY_CONCEPT_1: [Important concept to understand]
KEY_CONCEPT_2: [Another important concept]
FIX_OR_EXAMPLE: [Show corrected code OR a better example]
```

**MODE: DRAWING**
Use when user points at something they want to draw, sketch, or create artistically. Also use if they point at existing art and want to learn the technique.
```
MODE: DRAWING
TITLE: [2-4 word title]
SUBJECT: [What they want to draw]
SEARCH_QUERY_1: [how to draw [subject] for beginners]
SEARCH_QUERY_2: [drawing [subject] step by step tutorial]
SEARCH_QUERY_3: [[subject] drawing techniques]
```

**MODE: YOUTUBE_TUTORIAL**
Use when the topic is best learned through video tutorials - practical skills, how-to guides, complex processes, demonstrations, or when user asks "how to add/make/create" something.
```
MODE: YOUTUBE_TUTORIAL
TITLE: [2-4 word title]
CONTEXT: [Brief explanation of what user wants to learn - 1 sentence]
SEARCH_QUERY_1: [foundational tutorial query - beginner level]
SEARCH_QUERY_2: [intermediate/practical tutorial query]
SEARCH_QUERY_3: [advanced/specific technique query]
```

**MODE: YOUTUBE_INFO**
Use when user points at a concept, object, phenomenon, or topic where watching explanatory videos would be most educational.
```
MODE: YOUTUBE_INFO
TITLE: [2-4 word title]
TOPIC: [What they're asking about]
SEARCH_QUERY_1: [overview/introduction video query]
SEARCH_QUERY_2: [detailed explanation video query]
SEARCH_QUERY_3: [real-world applications/examples video query]
```

**MODE: CUSTOM_PAGE**
Use when information can be conveyed in a single, focused page - definitions, key facts, comparisons, quick reference info, or concepts that don't need video.
```
MODE: CUSTOM_PAGE
TITLE: [2-4 word title]
MAIN_POINT: [The most important thing to know - 1 clear sentence]
KEY_FACT_1: [Important fact or detail]
KEY_FACT_2: [Important fact or detail]
KEY_FACT_3: [Important fact or detail]
INSIGHT: [Interesting insight or practical application]
```

**CRITICAL DECISION RULES:**
- MATH/CODE: Always use when equations or code are visible
- DRAWING: Always use when artistic creation is the goal
- YOUTUBE_TUTORIAL: Use for "how to do X", practical skills, processes, demonstrations
- YOUTUBE_INFO: Use for "what is X", explanations of concepts, phenomena
- CUSTOM_PAGE: Use for quick facts, definitions, comparisons that fit on one screen

**CONTEXT AWARENESS:**
- If user points at a table and mentions "add flowers" → MODE: YOUTUBE_TUTORIAL with queries about flower arrangements
- If user points at a drawing → MODE: DRAWING with queries about that art technique
- If user points at a concept that needs visual demonstration → MODE: YOUTUBE_INFO or YOUTUBE_TUTORIAL
- If user points at something needing quick reference info → MODE: CUSTOM_PAGE

**FORMAT RULES:**
- Always start with "MODE: [TYPE]"
- Keep titles short and descriptive (2-4 words)
- For YouTube modes, create diverse, specific search queries
- For CUSTOM_PAGE, make each point concise and impactful (one line each)
- No extra text outside the specified format
- Each field on a new line with exact labels shown above
"""
previous_mode = "custom_page" # modes: math, code, drawing, youtube_tutorial, youtube_info, custom_page

''' SETUP GEMINI API '''
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
GEMINI_API = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"


def gemini_generate_with_image(image_path: str, prompt_text: str, model: str = GEMINI_MODEL) -> str:
    """Generate content from image using Gemini API."""
    cv2_image = cv2.imread(image_path)
    if cv2_image is None:
        raise RuntimeError(f"Could not load image: {image_path}")
    
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
def parse_gemini_response(response_text):
    lines = response_text.strip().split('\n')
    mode = "custom_page"
    title = ""
    structured_content = {}
    
    # Extract mode
    mode_match = re.search(r'MODE:\s*(\S+(?:_\S+)?)', response_text, re.IGNORECASE)
    if mode_match:
        mode = mode_match.group(1).lower()
    
    # Extract title
    title_match = re.search(r'TITLE:\s*(.+)', response_text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    # Parse based on mode
    if mode == "math":
        steps = []
        solution = ""
        for line in lines:
            step_match = re.match(r'STEP_\d+:\s*(.+)', line, re.IGNORECASE)
            if step_match:
                steps.append(step_match.group(1).strip())
            sol_match = re.match(r'SOLUTION(?:_OR_FIX)?:\s*(.+)', line, re.IGNORECASE)
            if sol_match:
                solution = sol_match.group(1).strip()
        
        structured_content['steps'] = steps
        structured_content['solution'] = solution
    
    elif mode == "code":
        for line in lines:
            lang_match = re.match(r'LANGUAGE:\s*(.+)', line, re.IGNORECASE)
            if lang_match:
                structured_content['language'] = lang_match.group(1).strip()
            
            expl_match = re.match(r'EXPLANATION:\s*(.+)', line, re.IGNORECASE)
            if expl_match:
                structured_content['explanation'] = expl_match.group(1).strip()
            
            concept_match = re.match(r'KEY_CONCEPT_\d+:\s*(.+)', line, re.IGNORECASE)
            if concept_match:
                if 'concepts' not in structured_content:
                    structured_content['concepts'] = []
                structured_content['concepts'].append(concept_match.group(1).strip())
            
            fix_match = re.match(r'FIX_OR_EXAMPLE:\s*(.+)', line, re.IGNORECASE)
            if fix_match:
                structured_content['fix_or_example'] = fix_match.group(1).strip()
    
    elif mode in ["drawing", "youtube_tutorial", "youtube_info"]:
        search_queries = []
        
        # Extract context/subject/topic
        for line in lines:
            context_match = re.match(r'(?:CONTEXT|SUBJECT|TOPIC):\s*(.+)', line, re.IGNORECASE)
            if context_match:
                structured_content['context'] = context_match.group(1).strip()
            
            query_match = re.match(r'SEARCH_QUERY_\d+:\s*(.+)', line, re.IGNORECASE)
            if query_match:
                search_queries.append(query_match.group(1).strip())
        
        structured_content['search_queries'] = search_queries
    
    elif mode == "custom_page":
        for line in lines:
            main_match = re.match(r'MAIN_POINT:\s*(.+)', line, re.IGNORECASE)
            if main_match:
                structured_content['main_point'] = main_match.group(1).strip()
            
            fact_match = re.match(r'KEY_FACT_\d+:\s*(.+)', line, re.IGNORECASE)
            if fact_match:
                if 'key_facts' not in structured_content:
                    structured_content['key_facts'] = []
                structured_content['key_facts'].append(fact_match.group(1).strip())
            
            insight_match = re.match(r'INSIGHT:\s*(.+)', line, re.IGNORECASE)
            if insight_match:
                structured_content['insight'] = insight_match.group(1).strip()
    
    return mode, title, structured_content
def generate_math_html(title, steps, solution):    
    html_files = []
    
    # Create a page for each step
    for i, step in enumerate(steps, 1):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Step {i}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5.5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #667eea;
                }}
                .step-number {{
                    font-size: 3vw;
                    color: #95a5a6;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 300;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(0,0,0,0.1);
                    max-width: 85vw;
                    border: 3px solid #667eea;
                }}
                .step-text {{
                    font-size: 4vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>
            <h1>📐 {title}</h1>
            <div class="step-number">Step {i} of {len(steps)}</div>
            <div class="content">
                <div class="step-text">{step}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    # Create a final page for the solution
    if solution:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Solution</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5.5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #667eea;
                }}
                .step-number {{
                    font-size: 3vw;
                    color: #27ae60;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 600;
                }}
                .content {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(102, 126, 234, 0.4);
                    max-width: 85vw;
                }}
                .solution-text {{
                    font-size: 4.5vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #ffffff;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <h1>📐 {title}</h1>
            <div class="step-number">✓ SOLUTION</div>
            <div class="content">
                <div class="solution-text">{solution}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    return html_files
def generate_code_html(title, language, explanation, concepts, fix_or_example):
    html_files = []
    
    # Page 1: Language and Explanation
    if explanation:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Overview</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #2c5364;
                }}
                .language {{
                    font-size: 3vw;
                    color: #27ae60;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 600;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(0,0,0,0.1);
                    max-width: 85vw;
                    border: 3px solid #2c5364;
                }}
                .text {{
                    font-size: 3.5vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>
            <h1>💻 {title}</h1>
            <div class="language">Language: {language}</div>
            <div class="content">
                <div class="text">{explanation}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    # Create a page for each key concept
    for i, concept in enumerate(concepts, 1):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Concept {i}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #2c5364;
                }}
                .concept-number {{
                    font-size: 3vw;
                    color: #64b5f6;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 600;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(0,0,0,0.1);
                    max-width: 85vw;
                    border-left: 8px solid #64b5f6;
                }}
                .concept-text {{
                    font-size: 3.5vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>
            <h1>💻 {title}</h1>
            <div class="concept-number">Key Concept {i}</div>
            <div class="content">
                <div class="concept-text">{concept}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    # Final page: Fix or Example
    if fix_or_example:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Example/Fix</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #2c5364;
                }}
                .subtitle {{
                    font-size: 3vw;
                    color: #27ae60;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 600;
                }}
                .content {{
                    background: #263238;
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(0,0,0,0.2);
                    max-width: 85vw;
                    border: 3px solid #27ae60;
                }}
                .code-text {{
                    font-size: 3vw;
                    color: #aed581;
                    text-align: center;
                    line-height: 1.8;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
            </style>
        </head>
        <body>
            <h1>💻 {title}</h1>
            <div class="subtitle">✓ Example / Fix</div>
            <div class="content">
                <div class="code-text">{fix_or_example}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    return html_files
def generate_custom_page_html(title, main_point, key_facts, insight):
    html_files = []
    
    # Page 1: Main Point
    if main_point:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Main Point</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 6vw;
                    margin-bottom: 8vh;
                    text-align: center;
                    color: #134e5e;
                }}
                .content {{
                    background: linear-gradient(135deg, #134e5e 0%, #71b280 100%);
                    padding: 6vh 7vw;
                    border-radius: 35px;
                    box-shadow: 0 15px 60px rgba(19, 78, 94, 0.3);
                    max-width: 85vw;
                }}
                .main-text {{
                    font-size: 4vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #ffffff;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <h1>💡 {title}</h1>
            <div class="content">
                <div class="main-text">{main_point}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    # Create a page for each key fact
    for i, fact in enumerate(key_facts, 1):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Fact {i}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5.5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #134e5e;
                }}
                .fact-number {{
                    font-size: 3vw;
                    color: #71b280;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 600;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(0,0,0,0.1);
                    max-width: 85vw;
                    border-left: 8px solid #71b280;
                }}
                .fact-text {{
                    font-size: 3.8vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>
            <h1>💡 {title}</h1>
            <div class="fact-number">Key Fact {i}</div>
            <div class="content">
                <div class="fact-text">• {fact}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    # Final page: Insight
    if insight:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title} - Insight</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #ffffff;
                    color: #2c3e50;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                    padding: 50px;
                }}
                h1 {{
                    font-size: 5.5vw;
                    margin-bottom: 2vh;
                    text-align: center;
                    color: #134e5e;
                }}
                .subtitle {{
                    font-size: 3vw;
                    color: #f39c12;
                    text-align: center;
                    margin-bottom: 5vh;
                    font-weight: 600;
                }}
                .content {{
                    background: linear-gradient(135deg, #f39c12 0%, #f1c40f 100%);
                    padding: 5vh 6vw;
                    border-radius: 30px;
                    box-shadow: 0 10px 50px rgba(243, 156, 18, 0.3);
                    max-width: 85vw;
                    border: 3px solid #f39c12;
                }}
                .insight-text {{
                    font-size: 3.8vw;
                    text-align: center;
                    line-height: 1.6;
                    color: #ffffff;
                    font-style: italic;
                    font-weight: 600;
                }}
            </style>
        </head>
        <body>
            <h1>💡 {title}</h1>
            <div class="subtitle">✨ Insight</div>
            <div class="content">
                <div class="insight-text">{insight}</div>
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_files.append('file://' + f.name)
    
    return html_files
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
def process_image(image_path, prompt):    
    # Get Gemini response
    gemini_response = gemini_generate_with_image(image_path, prompt)
    rospy.loginfo(f"process_image.py: Gemini response:\n{gemini_response}")
    
    # Parse response
    current_mode, title, structured_content = parse_gemini_response(gemini_response)
    urls = []
    scene_description = title
    
    # Handle different modes
    if current_mode == "math":
        steps = structured_content.get('steps', [])
        solution = structured_content.get('solution', '')
        # Generate HTML page
        urls = generate_math_html(title, steps, solution)
    
    elif current_mode == "code":
        language = structured_content.get('language', 'Code')
        explanation = structured_content.get('explanation', '')
        concepts = structured_content.get('concepts', [])
        fix_or_example = structured_content.get('fix_or_example', '')
        # Generate HTML page
        urls = generate_code_html(title, language, explanation, concepts, fix_or_example)
            
    elif current_mode == "custom_page":
        main_point = structured_content.get('main_point', '')
        key_facts = structured_content.get('key_facts', [])
        insight = structured_content.get('insight', '')       
        # Generate custom HTML page
        urls = generate_custom_page_html(title, main_point, key_facts, insight)
        
    elif current_mode in ["drawing", "youtube_tutorial", "youtube_info"]:
        # For YouTube modes, return search queries
        search_queries = structured_content.get('search_queries', [])
        #print(search_queries)
        # use search queries small phrases to create YouTube search URLs
        urls = search_yt_urls(search_queries)
    
    return current_mode, urls, scene_description


def callback(msg):
    global previous_mode

    image_id = msg.ID
    image_path = msg.path
    rospy.loginfo(f"process_image.py: Received image with ID: {image_id} and path: {image_path}")

    try:
        current_mode, urls, scene_description = process_image(image_path, PROMPT)
        
        url_msg.ID = image_id
        url_msg.scene_description = scene_description
        url_msg.prev_mode = previous_mode
        url_msg.current_mode = current_mode
        url_msg.url_list = urls
        url_msg.i = 0

        pub.publish(url_msg)
        rospy.loginfo(f"process_image.py: Published - Mode: {current_mode}, URLs: {len(urls)}")

        previous_mode = current_mode
        
    except Exception as e:
        rospy.logerr(f"process_image.py: Error processing image: {str(e)}")
        import traceback
        rospy.logerr(traceback.format_exc())

  
if __name__ == '__main__':
    rospy.init_node('process_image_gemini')
    sub = rospy.Subscriber('/point_image', PointingObject, callback)
    pub = rospy.Publisher('/urls_to_open', UrlToOpen, queue_size=1)
    url_msg = UrlToOpen()

    rospy.loginfo("process_image.py: Node started. Ready to analyze images!")
    rospy.spin()