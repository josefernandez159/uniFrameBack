from flask import Flask, request, jsonify, send_from_directory
import requests
from moviepy.editor import VideoFileClip
import speech_recognition as sr
import os
from googletrans import Translator

app = Flask(__name__)

# Diretório onde os arquivos de áudio serão salvos
AUDIO_DIR = 'audio_files'
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

def download_video(video_url, temp_video_path):
    try:
        # Baixa o vídeo
        video_response = requests.get(video_url, stream=True)
        video_response.raise_for_status()  # Levanta um erro para status HTTP inválidos
        
        # Salva o vídeo temporariamente
        with open(temp_video_path, 'wb') as video_file:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    video_file.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o vídeo: {e}")
        return False

def download_and_convert_to_audio(video_url, temp_audio_path, start_time=30, end_time=45):
    temp_video_path = "temp_video.mp4"
    
    if not download_video(video_url, temp_video_path):
        return None
    
    try:
        # Carrega o vídeo e corta o trecho desejado
        video_clip = VideoFileClip(temp_video_path).subclip(start_time, end_time)
        
        # Extrai o áudio e salva como WAV diretamente
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(temp_audio_path, codec='pcm_s16le')

        # Fecha os clipes para liberar recursos
        audio_clip.close()
        video_clip.close()
        
        # Remove o arquivo de vídeo temporário
        os.remove(temp_video_path)
        
        return temp_audio_path
    except Exception as e:
        print(f"Erro ao processar o vídeo: {e}")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        return None

def convert_audio_to_text(audio_path, output_text_path):
    # Inicializa o reconhecedor de fala
    recognizer = sr.Recognizer()
    
    # Carrega o arquivo de áudio WAV
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        
        # Reconhece a fala no áudio usando o Google Web Speech API
        try:
            text = recognizer.recognize_google(audio_data, language='en-CA')  # Substitua 'pt-BR' pelo idioma desejado
            with open(output_text_path, 'w', encoding='utf-8') as text_file:
                text_file.write(text)
            print("Transcrição concluída com sucesso!")
            return text
        except sr.UnknownValueError:
            print("Google Web Speech API não conseguiu entender o áudio")
        except sr.RequestError as e:
            print(f"Erro ao solicitar resultados do serviço Google Web Speech API; {e}")
    except Exception as e:
        print(f"Erro ao carregar o arquivo de áudio: {e}")
    return None

def translate_text_to_spanish(input_text):
    try:
        # Inicializa o tradutor
        translator = Translator()
        
        # Traduz o texto para o espanhol
        translated = translator.translate(input_text, src='pt', dest='es')
        
        print("Tradução concluída com sucesso!")
        return translated.text
    except Exception as e:
        print(f"Erro ao traduzir o texto: {e}")
        return None

@app.route('/process_video', methods=['GET'])
def process_video():
    video_url = request.args.get('video_url')
    
    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400
    
    temp_audio_path = os.path.join(AUDIO_DIR, "temp_audio.wav")
    output_text_path = "output_text.txt"
    
    audio_path = download_and_convert_to_audio(video_url, temp_audio_path)
    if not audio_path:
        return jsonify({"error": "Failed to process video"}), 500
    
    text = convert_audio_to_text(audio_path, output_text_path)
    if not text:
        return jsonify({"error": "Failed to transcribe audio"}), 500
    
    translated_text = translate_text_to_spanish(text)
    if not translated_text:
        return jsonify({"error": "Failed to translate text"}), 500
    
    audio_url = request.url_root + 'audio/' + os.path.basename(temp_audio_path)
    
    return jsonify({
        "audio_url": audio_url,
        "text": text,
        "translated_text": translated_text
    })

@app.route('/audio/<path:filename>', methods=['GET'])
def download_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 1001))
    app.run(debug=True, port=port)
