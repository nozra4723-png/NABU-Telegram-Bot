import os
import io
import telebot
from telebot import types
import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv

# 1. إعداد المفاتيح
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  
GROQ_API_KEY = os.getenv("GROQ_API_KEY")      

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

user_data = {}

# 2. رسالة الترحيب والواجهة الرئيسية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🏛️ **أهلاً بك في صرح نابو للذكاء الأكاديمي (NABU AI)**\n"
        "المساعد الأكاديمي الشامل والمطور بواسطة **المهندس عباس قصي**.\n\n"
        "✨ **ماذا يمكنني أن أفعل لك؟**\n"
        "📄 **كتابة تقرير أكاديمي خارق:** أرسل لي أي عنوان موضوع في الحياة، وسأكتب لك تقريراً شاملاً وموثقاً.\n"
        "📚 **تحليل الملازم والـ PDF:** أرسل أي ملف ملزمة لتلخيصها، حل مسائلها، أو عمل أسئلة واختبارات.\n"
        "🧮 **حل المسائل الرياضية والبرمجية:** أرسل أي سؤال أو كود وسأحله لك خطوة بخطوة.\n\n"
        "👇 **اختر من القائمة أدناه للبدء فوراً:**"
    )
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_report = types.KeyboardButton("📄 إنشاء تقرير أكاديمي شامل")
    btn_solve = types.KeyboardButton("🧮 حل مسألة / كود برمجي")
    btn_quiz = types.KeyboardButton("📊 توليد أسئلة واختبارات")
    btn_help = types.KeyboardButton("💡 كيف أستخدم البوت؟")
    markup.add(btn_report, btn_solve, btn_quiz, btn_help)
    
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

# 3. ميزة إنشاء التقارير الأكاديمية الشاملة عن أي موضوع
@bot.message_handler(func=lambda message: message.text == "📄 إنشاء تقرير أكاديمي شامل")
def ask_for_report_topic(message):
    msg = bot.reply_to(
        message, 
        "✍️ **أكتب لي اسم أو عنوان الموضوع الذي تريد إنشاء التقرير عنه**\n"
        "(مثال: الذكاء الاصطناعي في الطب، الطاقة المتجددة، تاريخ العمارة بابل...)"
    )
    bot.register_next_step_handler(msg, generate_full_report)

def generate_full_report(message):
    topic = message.text
    status_msg = bot.reply_to(message, "🏛️ **نابو يجمع المصادر ويكتب التقرير الأكاديمي الشامل الآن...**")
    
    system_prompt = (
        "أنت 'نابو' (NABU AI)، الباحث والأستاذ الأكاديمي الخبير.\n"
        "تم تطويرك بالكامل بواسطة المهندس عباس قصي (Abbas Qusay).\n"
        "المطلوب منك: كتابة تقرير أكاديمي جامع، متكامل، ومفصل جداً حول الموضوع المحدد.\n\n"
        "هيكلية التقرير الواجب اتباعها:\n"
        "1. المقدمة والأهمية العلمية.\n"
        "2. المحاور الرئيسية والشرح النظري التفصيلي.\n"
        "3. التطبيقات العملية وأمثلة من الواقع.\n"
        "4. التحديات والآفاق المستقبلية.\n"
        "5. الخاتمة والاستنتاج الأكاديمي.\n"
        "استخدم أسلوباً لغوياً فخماً، واكتفِ بالمعلومات الأكاديمية الدقيقة."
    )
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"اكتب تقريراً أكاديمياً متكاملاً عن: {topic}"}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        report_content = response.choices[0].message.content
        
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(message.chat.id, f"📋 **تقرير أكاديمي حول: {topic}**\n\n{report_content}", parse_mode="Markdown")
        
        report_file = io.BytesIO(report_content.encode('utf-8'))
        report_file.name = f"تقرير_{topic.replace(' ', '_')}.txt"
        bot.send_document(message.chat.id, report_file, caption="📥 **نسخة الملف الجاهزة للتحميل والتنسيق**")
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ أثناء إعداد التقرير: {e}")

# 4. استقبال ومعالجة ملفات الـ PDF (الملازم)
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.mime_type == 'application/pdf':
        status_msg = bot.reply_to(message, "📖 **جاري قراءة وتحليل ملف PDF...**")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text("text") + "\n"
            
        user_data[message.chat.id] = extracted_text[:30000] 
        
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.reply_to(
            message, 
            f"✅ **تمت قراءة الملزمة بنجاح! ({len(extracted_text)} حرف)**\n\n"
            "الآن يمكنك أن تطلب مني أي شيء:\n"
            "- ملخص الملزمة\n"
            "- حل مسائل الملزمة\n"
            "- أسئلة وأجوبة\n"
            "- أو اسألني عن أي جزء محدد بها!"
        )
    else:
        bot.reply_to(message, "يرجى إرسال ملف بصيغة PDF فقط.")

# 5. معالجة الأسئلة المباشرة والنصوص
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_prompt = message.text
    context_text = user_data.get(message.chat.id, "")
    
    status_msg = bot.reply_to(message, "🏛️ **نابو يفكر ويحلل...**")
    
    system_prompt = (
        "أنت 'نابو' (NABU AI)، المساعد الأكاديمي الخارق والأستاذ الجامعي.\n"
        "تم تطويرك بالكامل بواسطة المهندس عباس قصي (Abbas Qusay).\n"
        "أجب بدقة، وضوح، وحل المسائل الرياضية والبرمجية خطوة بخطوة مع استخدام LaTeX للمعادلات."
    )
    
    full_prompt = f"المحتوى المرفوع:\n{context_text}\n\nالسؤال/الطلب:\n{user_prompt}" if context_text else user_prompt
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.4,
            max_tokens=3000
        )
        answer = response.choices[0].message.content
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.reply_to(message, answer, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ أثناء المعالجة: {e}")

# تشغيل البوت
bot.polling(none_stop=True)
