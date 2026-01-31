import streamlit as st
import google.generativeai as genai
import sqlite3
import json
import instaloader
from PIL import Image
import re

# --- CONFIGURATION SÉCURISÉE ---
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("Clé API manquante ! Configurez le secrets Streamlit.")

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

    /* Fond Gris Clair Apple officiel */
    .stApp {
        background-color: #F2F2F7 !important;
    }

    /* Police Apple partout */
    * {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Cartes Blanches GoomY (Expanders) */
    div[data-testid="stExpander"] {
        background-color: white !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
        margin-bottom: 15px !important;
    }

    /* Nettoyage de l'entête des cartes */
    .streamlit-expanderHeader {
        border: none !important;
        font-size: 17px !important;
        font-weight: 600 !important;
        color: #1C1C1E !important;
    }

    /* Bouton vert GoomY Pro */
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

    /* Badges iOS (Temps et Calories) */
    .badge-t { 
        background: #F2F2F7; 
        padding: 6px 14px; 
        border-radius: 10px; 
        font-size: 13px; 
        font-weight: 600; 
        color: #3A3A3C; 
        margin-right: 8px;
        border: 1px solid #E5E5EA;
    }
    .badge-c { 
        background: #FFF9E6; 
        padding: 6px 14px; 
        border-radius: 10px; 
        font-size: 13px; 
        font-weight: 600; 
        color: #FF9500; 
        border: 1px solid #FFE6A5;
    }

    /* Style du sélecteur de portions */
    div[data-testid="stNumberInput"] {
        background-color: #F2F2F7 !important;
        border-radius: 12px !important;
    }

    /* Titres et textes */
    h1 { font-weight: 800 !important; letter-spacing: -1px !important; color: #000000 !important; }
    h3 { font-weight: 700 !important; color: #1C1C1E !important; margin-top: 20px !important; }
    p, li { color: #3A3A3C !important; line-height: 1.6 !important; }
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
                    st.error("Erreur de format IA. Réessaie !")

# --- LISTE DES RECETTES ---
st.write("### Mes Recettes")
conn = sqlite3.connect('recipes.db')
c = conn.cursor()
c.execute("SELECT * FROM recipes ORDER BY id DESC")
rows = c.fetchall() 

# Fonction pour multiplier les quantités numériques
def multiplier_ingredients(texte, coef):
    def replace_num(match):
        num_str = match.group().replace(',', '.')
        try:
            num = float(num_str)
            return str(round(num * coef, 1)).replace('.0', '')
        except:
            return num_str
    return re.sub(r'\d+([.,]\d+)?', replace_num, texte)

for r in rows:
    id_recette, titre, auteur, temps, kcal_base, ingredients, etapes = r
    
    with st.expander(f"🍽️ {titre} — {temps}", expanded=False):
        # --- LIGNE D'INFO ET SÉLECTEUR DE PORTIONS ---
        col_info, col_qty = st.columns([2, 1])
        
        with col_info:
            st.markdown(f"<p style='color:#8E8E93; font-size:14px; margin-bottom:10px;'>Par {auteur}</p>", unsafe_allow_html=True)
            st.markdown(f"<span class='badge-t'>⏱️ {temps}</span><span class='badge-c'>🔥 {kcal_base}</span>", unsafe_allow_html=True)
        
        with col_qty:
            # Sélecteur interactif (Base 4 personnes)
            nb_pers = st.number_input("Pers.", min_value=1, max_value=20, value=4, key=f"qty_{id_recette}", label_visibility="collapsed")
            st.markdown(f"<p style='text-align:center; font-size:12px; color:#8E8E93;'>Portions: {nb_pers}</p>", unsafe_allow_html=True)

        st.subheader("🛒 Ingrédients")
        ratio = nb_pers / 4 
        ing_ajustes = multiplier_ingredients(ingredients, ratio)
        st.markdown(ing_ajustes.replace("•", "\n\n•")) 
        
        st.subheader("👨‍🍳 Préparation")
        st.markdown(etapes.replace("•", "\n\n•"))
        
        st.divider()
        if st.button(f"🗑️ Supprimer", key=f"del_{id_recette}"):
            with sqlite3.connect('recipes.db') as conn_del:
                c_del = conn_del.cursor()
                c_del.execute("DELETE FROM recipes WHERE id=?", (id_recette,))
                conn_del.commit()
            st.rerun()

conn.close()