import streamlit as st
import google.generativeai as genai
import sqlite3
import json
import instaloader
from PIL import Image

# --- CONFIGURATION SÉCURISÉE ---
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    API_KEY = "AIzaSyC9FTjyw83h1MSAtKNQXSGUW2_d6SJ8MPY" 

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
L = instaloader.Instaloader()

# --- BASE DE DONNÉES ---
def init_db():
    conn = sqlite3.connect('recipes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY, titre TEXT, auteur TEXT, temps TEXT, kcal TEXT, ingredients TEXT, etapes TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- DESIGN "PURE GOOMY" (iOS NATIVE LOOK) ---
st.set_page_config(page_title="Mon GoomY", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/sf-pro-display');

    /* Fond Gris Clair Apple */
    .stApp {
        background-color: #F2F2F7 !important;
    }

    /* Police Partout */
    * {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Cartes Blanches GoomY */
    div[data-testid="stExpander"] {
        background-color: white !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
        margin-bottom: 15px !important;
    }

    /* Supprimer la ligne de bordure Streamlit par défaut */
    .streamlit-expanderHeader {
        border: none !important;
        font-size: 17px !important;
        font-weight: 600 !important;
        color: #1C1C1E !important;
    }

    /* Bouton vert Apple Style */
    .stButton>button {
        border-radius: 15px !important;
        background-color: #34C759 !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
        height: 52px !important;
        width: 100% !important;
        font-size: 16px !important;
    }

    /* Badges iOS */
    .badge-t { 
        background: #E5E5EA; 
        padding: 6px 14px; 
        border-radius: 10px; 
        font-size: 13px; 
        font-weight: 600; 
        color: #3A3A3C; 
        margin-right: 8px;
    }
    .badge-c { 
        background: #FFF9E6; 
        padding: 6px 14px; 
        border-radius: 10px; 
        font-size: 13px; 
        font-weight: 600; 
        color: #FF9500; 
    }

    /* Titres et textes */
    h1 { font-weight: 800 !important; letter-spacing: -1px !important; color: #000000 !important; }
    h3 { font-weight: 700 !important; color: #1C1C1E !important; margin-top: 15px !important; }
    p, li { color: #3A3A3C !important; line-height: 1.5 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("👨‍🍳 Mon GoomY")

# --- ZONE D'AJOUT ---
with st.container():
    source_link = st.text_input("Lien Instagram", placeholder="Colle le lien ici...")
    uploaded_file = st.file_uploader("Ou Capture d'écran", type=["png", "jpg", "jpeg"])
    
    if st.button("🚀 Extraire la recette"):
        with st.spinner("L'IA travaille..."):
            content, img = "", None
            if uploaded_file:
                img = Image.open(uploaded_file)
                content = "Analyse cette image."
            elif source_link:
                try:
                    shortcode = source_link.split("/")[-2]
                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    content = post.caption
                except:
                    content = f"Lien : {source_link}"
            
            if content:
                prompt = """Réponds UNIQUEMENT en JSON. 
                - 'ingredients' : chaque ligne doit commencer par '• '.
                - 'etapes' : chaque étape doit commencer par '• '. Si absentes, DEVIINE-LES logiquement.
                Format : {"titre": "...", "auteur": "...", "temps": "...", "kcal": "...", "ingredients": "...", "etapes": "..."}"""
                
                try:
                    res = model.generate_content([prompt, img]) if img else model.generate_content(f"{prompt} {content}")
                    clean_res = res.text.replace('```json', '').replace('```', '').strip()
                    data = json.loads(clean_res)
                    
                    conn = sqlite3.connect('recipes.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO recipes (titre, auteur, temps, kcal, ingredients, etapes) VALUES (?,?,?,?,?,?)",
                              (data.get('titre', 'Sans titre'), data.get('auteur', 'Inconnu'), 
                               data.get('temps', 'N/A'), data.get('kcal', 'N/A'), 
                               data.get('ingredients', ''), data.get('etapes', '')))
                    conn.commit()
                    conn.close()
                    st.rerun()
                except:
                    st.error("Erreur. Réessaie avec une capture !")

# --- LISTE DES RECETTES ---
st.write("### Mes Recettes")
conn = sqlite3.connect('recipes.db')
c = conn.cursor()
c.execute("SELECT * FROM recipes ORDER BY id DESC")
rows = c.fetchall() 

for r in rows:
    # On affiche le titre et le temps directement dans l'entête
    with st.expander(f"🍽️ {r[1]} — {r[3]}", expanded=False):
        st.markdown(f"<p style='color:#8E8E93; font-size:14px; margin-bottom:12px;'>Par {r[2]}</p>", unsafe_allow_html=True)
        st.markdown(f"<span class='badge-t'>⏱️ {r[3]}</span><span class='badge-c'>🔥 {r[4]}</span>", unsafe_allow_html=True)
        
        st.subheader("🛒 Ingrédients")
        # On force l'affichage en liste propre
        ing = r[5].replace("•", "\n\n•").replace("  ", " ")
        st.markdown(ing) 
        
        st.subheader("👨‍🍳 Préparation")
        prep = r[6].replace("•", "\n\n•").replace("  ", " ")
        st.markdown(prep)
        
        st.divider()
        if st.button(f"🗑️ Supprimer", key=f"del_{r[0]}"):
            with sqlite3.connect('recipes.db') as conn_del:
                c_del = conn_del.cursor()
                c_del.execute("DELETE FROM recipes WHERE id=?", (r[0],))
                conn_del.commit()
            st.rerun()

conn.close()