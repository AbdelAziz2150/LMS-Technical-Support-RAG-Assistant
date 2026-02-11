import os
import io
import time
import threading
import base64
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from PIL import Image
from docx import Document as DocxDocument
from openai import OpenAI
import secrets

# --------------------------- 
# Setup 
# --------------------------- 
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

UPLOAD_FOLDER = './uploaded_docs'
ALLOWED_EXTENSIONS = {'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def prepare_image_for_vision(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# --------------------------- 
# RAG SYSTEM 
# --------------------------- 
class LearningCurveRAG:
    def __init__(self, docs_dir):
        self.text_model = "gpt-5.2"
        self.vision_model = "gpt-5.2"
        self.docs_dir = Path(docs_dir)
        self.queue_dir = Path("./image_queue")
        self.queue_dir.mkdir(exist_ok=True)
        
        self.chroma = chromadb.PersistentClient(path="./chroma_db")
        self.embedder = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-large"
        )
        
        self.collection = self.chroma.get_or_create_collection(
            name="learningcurve_rag",
            embedding_function=self.embedder
        )
        
        threading.Thread(target=self._vision_worker, daemon=True).start()
        print(f"--- Initializing Knowledge Base from {docs_dir} ---")
        self.create_vectorstore()
    
    def _vision_worker(self):
        while True:
            images = list(self.queue_dir.glob("*.png"))
            if not images:
                time.sleep(10)
                continue
            
            for img_path in images:
                try:
                    doc_id = img_path.stem
                    meta_list = self.collection.get(ids=[doc_id])["metadatas"]
                    if not meta_list:
                        continue
                    
                    meta = meta_list[0]
                    if meta.get("processed"):
                        img_path.unlink(missing_ok=True)
                        continue
                    
                    with open(img_path, "rb") as f:
                        image_b64 = prepare_image_for_vision(f.read())
                    
                    description = self.describe_image(image_b64)
                    
                    self.collection.update(
                        ids=[doc_id],
                        documents=[description],
                        metadatas=[{"processed": True, "type": "image", "source": meta["source"]}]
                    )
                    
                    img_path.unlink(missing_ok=True)
                    
                except Exception as e:
                    print(f"\n[Vision Error]: {e}")
            
            time.sleep(10)
    
    def describe_image(self, image_b64: str) -> str:
        resp = client.chat.completions.create(
            model=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this LMS screenshot in detail for a technical manual. "
                            "For every button, icon, and navigation element: "
                            "1. Identify the visual shape (e.g., megaphone, gear, plus sign). "
                            "2. Note the color and screen location (e.g., top-right header, sidebar). "
                            "3. State the associated text label. "
                            "Explain the purpose of this screen as if teaching a new user."
                        )
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            }]
        )
        return resp.choices[0].message.content.strip()
    
    def process_docx(self, path: str):
        doc = DocxDocument(path)
        file_name = os.path.basename(path)
        
        if self.collection.get(where={"source": file_name})["ids"]:
            return
        
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        chunks = [text[i:i+2000] for i in range(0, len(text), 1800)]
        
        self.collection.add(
            ids=[f"{file_name}_t_{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[{"source": file_name, "type": "text"}] * len(chunks)
        )
        
        img_index = 0
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                img_id = f"{file_name}_img_{img_index}"
                with open(self.queue_dir / f"{img_id}.png", "wb") as f:
                    f.write(rel.target_part.blob)
                
                self.collection.add(
                    ids=[img_id],
                    documents=["[Image queued for analysis]"],
                    metadatas=[{"source": file_name, "processed": False, "type": "image"}]
                )
                img_index += 1
    
    def create_vectorstore(self):
        for file in self.docs_dir.rglob("*.docx"):
            self.process_docx(str(file))
    
    def ask(self, question: str):
        results = self.collection.query(query_texts=[question], n_results=6)
        context = "\n\n".join(results["documents"][0])
        
        prompt = (
            f"You are a specialized LMS Technical Support Assistant. "
            f"Your goal is to provide a walkthrough that is impossible to misunderstand.\n\n"
            f"RULES:\n"
            f"1. For every action, describe the visual icon (e.g., 'the megaphone icon') and its screen location.\n"
            f"2. Use both the text documentation AND the image descriptions provided in the context.\n"
            f"3. If an icon is mentioned but not described, use the image analysis to find its shape/color.\n"
            f"4. Be conversational but extremely precise. Answer ONLY using the provided context.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {question}"
        )
        
        response = client.chat.completions.create(
            model=self.text_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.01
        )
        
        return response.choices[0].message.content

# Initialize RAG system
bot = LearningCurveRAG(UPLOAD_FOLDER)

# --------------------------- 
# Flask Routes 
# --------------------------- 

@app.route('/')
def index():
    return render_template('UI.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the document
        try:
            bot.process_docx(filepath)
            return jsonify({'message': f'File {filename} uploaded and processed successfully!'}), 200
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Only .docx files are allowed.'}), 400

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        def generate():
            results = bot.collection.query(query_texts=[question], n_results=6)
            context = "\n\n".join(results["documents"][0])
            
            prompt = (
                f"You are a specialized LMS Technical Support Assistant. "
                f"Your goal is to provide a walkthrough that is impossible to misunderstand.\n\n"
                f"CRITICAL FORMATTING RULES:\n"
                f"- Use '## 1)' '## 2)' '## 3)' etc. for main steps\n"
                f"- Use '1.' '2.' '3.' etc. for sub-steps under each main step\n"
                f"- IMPORTANT: Put each sub-step on a NEW LINE (press Enter after each sub-step)\n"
                f"- Example format:\n"
                f"  ## 1) Main step title\n"
                f"  1. First sub-step here.\n"
                f"  2. Second sub-step here.\n"
                f"  3. Third sub-step here.\n"
                f"  ## 2) Next main step\n\n"
                f"CONTENT RULES:\n"
                f"- For every action, describe the visual icon (e.g., 'the megaphone icon') and its screen location\n"
                f"- Use **bold** for important UI elements, colors, and locations\n"
                f"- Be conversational but extremely precise\n"
                f"- Answer ONLY using the provided context\n"
                f"- Use both text documentation AND image descriptions\n\n"
                f"CONTEXT:\n{context}\n\n"
                f"USER QUESTION: {question}"
            )
            
            stream = client.chat.completions.create(
                model=bot.text_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.01,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"
            
            yield "data: [DONE]\n\n"
        
        return app.response_class(generate(), mimetype='text/event-stream')
    except Exception as e:
        return jsonify({'error': f'Error processing question: {str(e)}'}), 500

@app.route('/documents', methods=['GET'])
def list_documents():
    try:
        # Get unique sources from the collection
        all_metadata = bot.collection.get()['metadatas']
        sources = list(set([meta.get('source', 'Unknown') for meta in all_metadata]))
        return jsonify({'documents': sources}), 200
    except Exception as e:
        return jsonify({'error': f'Error listing documents: {str(e)}'}), 500

@app.route('/queue-status', methods=['GET'])
def queue_status():
    try:
        # Count images in the queue directory (waiting to be processed)
        # Use the SAME order as the vision worker uses (glob returns lexicographic order)
        pending_images = sorted(list(bot.queue_dir.glob("*.png")))
        pending_count = len(pending_images)
        
        # Get the first image being processed (same as vision worker logic)
        current_image = None
        if pending_images:
            # The vision worker processes in the order glob returns them (alphabetically)
            # So we check each one in order to find the first unprocessed one
            for img_path in pending_images:
                try:
                    doc_id = img_path.stem
                    meta_list = bot.collection.get(ids=[doc_id])["metadatas"]
                    if not meta_list:
                        continue
                    
                    meta = meta_list[0]
                    # Skip already processed images
                    if meta.get("processed"):
                        continue
                    
                    # This is the current image being processed
                    current_image = {
                        'filename': img_path.name,
                        'source_doc': img_path.stem.rsplit('_img_', 1)[0] if '_img_' in img_path.stem else 'Unknown'
                    }
                    break
                except:
                    continue
        
        # Count total images and processed images in the database
        all_metadata = bot.collection.get()['metadatas']
        total_images = sum(1 for meta in all_metadata if meta.get('type') == 'image')
        processed_images = sum(1 for meta in all_metadata if meta.get('type') == 'image' and meta.get('processed', False))
        
        return jsonify({
            'pending_images': pending_count,
            'total_images': total_images,
            'processed_images': processed_images,
            'is_processing': pending_count > 0,
            'current_image': current_image
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error getting queue status: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)