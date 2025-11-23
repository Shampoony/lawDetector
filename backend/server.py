from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import shutil
import re
from docx import Document
from PyPDF2 import PdfReader
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
REPORT_DIR = ROOT_DIR / "reports"
UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Default dangerous keywords/phrases in Russian
DEFAULT_DANGEROUS_KEYWORDS = [
    "штраф", "пеня", "неустойка", "одностороннее расторжение",
    "безусловное обязательство", "автопролонгация", "безакцептное списание",
    "полная материальная ответственность", "без права отказа",
    "исключительные права", "бессрочное обязательство",
    "односторонний отказ", "полная ответственность за",
    "возмещение всех убытков", "неограниченная ответственность"
]

# Required sections in contracts
REQUIRED_SECTIONS = [
    "предмет договора",
    "стоимость",
    "срок",
    "ответственность сторон",
    "порядок разрешения споров",
    "реквизиты сторон"
]

# Define Models
class Keyword(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    keyword: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KeywordCreate(BaseModel):
    keyword: str

class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    risk_level: str
    dangerous_phrases: List[dict]
    missing_sections: List[str]
    ai_analysis: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper Functions
def extract_text_from_file(filepath: str) -> str:
    """Extract text from .txt, .docx, or .pdf files"""
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == '.docx':
            doc = Document(filepath)
            return '\n'.join([para.text for para in doc.paragraphs])
        
        elif ext == '.pdf':
            reader = PdfReader(filepath)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
            return text
        
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    except Exception as e:
        logging.error(f"Error extracting text from {filepath}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

def analyze_dangerous_phrases(text: str, keywords: List[str]) -> List[dict]:
    """Analyze text for dangerous phrases"""
    text_lower = text.lower()
    found_phrases = []
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        matches = re.finditer(re.escape(keyword_lower), text_lower)
        for match in matches:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            found_phrases.append({
                "phrase": keyword,
                "context": context,
                "position": match.start()
            })
    
    return found_phrases

def check_missing_sections(text: str) -> List[str]:
    """Check for missing required sections"""
    text_lower = text.lower()
    missing = []
    
    for section in REQUIRED_SECTIONS:
        if section.lower() not in text_lower:
            missing.append(section)
    
    return missing

def calculate_risk_level(dangerous_count: int, missing_count: int) -> str:
    """Calculate overall risk level"""
    total_issues = dangerous_count + (missing_count * 2)
    
    if total_issues >= 10:
        return "HIGH"
    elif total_issues >= 5:
        return "MEDIUM"
    else:
        return "LOW"

async def ai_analyze_contract(text: str) -> str:
    """Use AI to analyze contract for deeper insights"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"contract_analysis_{uuid.uuid4()}",
            system_message="Вы - эксперт по юридическому анализу договоров. Анализируйте договоры на предмет рисков, невыгодных условий и потенциальных проблем."
        ).with_model("openai", "gpt-5.1")
        
        prompt = f"""Проанализируйте следующий договор и выявите:
1. Основные риски для подписанта
2. Невыгодные или несправедливые условия
3. Потенциальные финансовые обязательства
4. Рекомендации по улучшению условий

Текст договора:
{text[:8000]}

Предоставьте краткий, но содержательный анализ."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
    
    except Exception as e:
        logging.error(f"AI analysis failed: {str(e)}")
        return f"AI анализ временно недоступен: {str(e)}"

def generate_html_report(analysis: AnalysisResult, text: str) -> str:
    """Generate HTML report"""
    risk_colors = {
        "LOW": "#22c55e",
        "MEDIUM": "#f59e0b",
        "HIGH": "#ef4444"
    }
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет по анализу договора - {analysis.filename}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0a0a0a;
            color: #e5e5e5;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 50px;
        }}
        .header h1 {{
            color: #00BFFF;
            font-size: 36px;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #888;
            font-size: 14px;
        }}
        .risk-badge {{
            display: inline-block;
            padding: 12px 30px;
            background: {risk_colors[analysis.risk_level]};
            color: white;
            border-radius: 25px;
            font-weight: bold;
            font-size: 18px;
            margin: 20px 0;
            box-shadow: 0 4px 20px rgba(0, 191, 255, 0.3);
        }}
        .section {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        }}
        .section h2 {{
            color: #00BFFF;
            font-size: 24px;
            margin-bottom: 20px;
            border-bottom: 2px solid #00BFFF;
            padding-bottom: 10px;
        }}
        .item {{
            background: #252525;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #00BFFF;
        }}
        .item-title {{
            color: #00BFFF;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .item-content {{
            color: #ccc;
            line-height: 1.6;
        }}
        .missing-item {{
            color: #ef4444;
            padding: 10px;
            margin-bottom: 10px;
            background: #2a1a1a;
            border-radius: 6px;
            border-left: 4px solid #ef4444;
        }}
        .ai-section {{
            background: linear-gradient(135deg, #1a2a3a 0%, #2a1a3a 100%);
            border: 1px solid #00BFFF;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 LawAssistant - Отчет по анализу</h1>
            <p>Файл: {analysis.filename}</p>
            <div class="risk-badge">Уровень риска: {analysis.risk_level}</div>
        </div>
        
        <div class="section">
            <h2>⚠️ Опасные фразы ({len(analysis.dangerous_phrases)})</h2>
            {_generate_dangerous_phrases_html(analysis.dangerous_phrases)}
        </div>
        
        <div class="section">
            <h2>📝 Отсутствующие разделы ({len(analysis.missing_sections)})</h2>
            {_generate_missing_sections_html(analysis.missing_sections)}
        </div>
        
        {_generate_ai_analysis_html(analysis.ai_analysis) if analysis.ai_analysis else ''}
        
        <div class="timestamp">
            Отчет создан: {analysis.created_at.strftime('%d.%m.%Y %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
    
    return html

def _generate_dangerous_phrases_html(phrases: List[dict]) -> str:
    if not phrases:
        return '<p class="item-content">Опасные фразы не обнаружены ✅</p>'
    
    html = ''
    for phrase in phrases:
        html += f'''<div class="item">
            <div class="item-title">{phrase['phrase']}</div>
            <div class="item-content">Контекст: ...{phrase['context']}...</div>
        </div>'''
    return html

def _generate_missing_sections_html(missing: List[str]) -> str:
    if not missing:
        return '<p class="item-content">Все обязательные разделы присутствуют ✅</p>'
    
    html = ''
    for section in missing:
        html += f'<div class="missing-item">❌ {section}</div>'
    return html

def _generate_ai_analysis_html(ai_analysis: Optional[str]) -> str:
    if not ai_analysis:
        return ''
    
    return f'''<div class="section ai-section">
        <h2>🤖 AI-анализ договора</h2>
        <div class="item-content" style="white-space: pre-wrap;">{ai_analysis}</div>
    </div>'''

# API Routes
@api_router.get("/")
async def root():
    return {"message": "LawAssistant API"}

@api_router.post("/keywords", response_model=Keyword)
async def add_keyword(input: KeywordCreate):
    """Add a custom keyword for analysis"""
    keyword_obj = Keyword(keyword=input.keyword)
    doc = keyword_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.keywords.insert_one(doc)
    return keyword_obj

@api_router.get("/keywords", response_model=List[Keyword])
async def get_keywords():
    """Get all custom keywords"""
    keywords = await db.keywords.find({}, {"_id": 0}).to_list(1000)
    for kw in keywords:
        if isinstance(kw['created_at'], str):
            kw['created_at'] = datetime.fromisoformat(kw['created_at'])
    return keywords

@api_router.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: str):
    """Delete a keyword"""
    result = await db.keywords.delete_one({"id": keyword_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return {"message": "Keyword deleted"}

@api_router.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    """Analyze uploaded contract"""
    # Validate file extension
    allowed_extensions = ['.txt', '.docx', '.pdf']
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file
    file_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text
        text = extract_text_from_file(str(filepath))
        
        if len(text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Document is too short or empty")
        
        # Get custom keywords
        try:
            custom_keywords = await db.keywords.find({}, {"_id": 0}).to_list(1000)
            all_keywords = DEFAULT_DANGEROUS_KEYWORDS + [kw['keyword'] for kw in custom_keywords]
        except Exception as e:
            logging.warning(f"Failed to fetch custom keywords: {str(e)}")
            all_keywords = DEFAULT_DANGEROUS_KEYWORDS
        
        # Perform analysis
        dangerous_phrases = analyze_dangerous_phrases(text, all_keywords)
        missing_sections = check_missing_sections(text)
        risk_level = calculate_risk_level(len(dangerous_phrases), len(missing_sections))
        
        # AI analysis (with timeout protection)
        try:
            ai_analysis = await ai_analyze_contract(text)
        except Exception as e:
            logging.warning(f"AI analysis failed, continuing without it: {str(e)}")
            ai_analysis = f"AI анализ временно недоступен: {str(e)}"
        
        # Create analysis result
        result = AnalysisResult(
            filename=file.filename,
            risk_level=risk_level,
            dangerous_phrases=dangerous_phrases,
            missing_sections=missing_sections,
            ai_analysis=ai_analysis
        )
        
        # Save to database
        try:
            doc = result.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            # Ensure no ObjectId fields are present
            if '_id' in doc:
                del doc['_id']
            insert_result = await db.analyses.insert_one(doc)
        except Exception as e:
            logging.error(f"Database save failed: {str(e)}")
            # Continue without saving to database for now
        
        # Generate reports
        json_path = REPORT_DIR / f"{result.id}.json"
        html_path = REPORT_DIR / f"{result.id}.html"
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save JSON report: {str(e)}")
            # Continue without saving JSON report
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(generate_html_report(result, text))
        
        # Create response with proper serialization
        response_data = {
            "id": str(result.id),
            "filename": str(result.filename),
            "risk_level": str(result.risk_level),
            "dangerous_phrases": result.dangerous_phrases,
            "missing_sections": result.missing_sections,
            "ai_analysis": str(result.ai_analysis) if result.ai_analysis else None,
            "created_at": result.created_at.isoformat()
        }
        
        # Ensure no ObjectId in dangerous_phrases
        for phrase in response_data["dangerous_phrases"]:
            for key, value in phrase.items():
                phrase[key] = str(value)
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up uploaded file
        if filepath.exists():
            filepath.unlink()

@api_router.get("/report/{report_id}/json")
async def download_json_report(report_id: str):
    """Download JSON report"""
    json_path = REPORT_DIR / f"{report_id}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(json_path, media_type="application/json", filename=f"report_{report_id}.json")

@api_router.get("/report/{report_id}/html")
async def download_html_report(report_id: str):
    """Download HTML report"""
    html_path = REPORT_DIR / f"{report_id}.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(html_path, media_type="text/html", filename=f"report_{report_id}.html")

@api_router.get("/history", response_model=List[dict])
async def get_analysis_history():
    """Get analysis history"""
    analyses = await db.analyses.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    for analysis in analyses:
        if isinstance(analysis.get('created_at'), str):
            analysis['created_at'] = datetime.fromisoformat(analysis['created_at'])
    return analyses

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
