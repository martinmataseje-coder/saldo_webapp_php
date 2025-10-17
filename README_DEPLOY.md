
# Saldo_1 – webový generátor (Streamlit)

## Lokálny beh
```
pip install -r requirements.txt
streamlit run app_streamlit.py
```
Otvor sa URL (napr. http://localhost:8501), nahraj 4 Excely, vyplň polia a klikni "Generovať".

## Docker
```
docker build -t saldo-app .
docker run -p 8501:8501 saldo-app
```
Potom otvor http://localhost:8501

## Nasadenie
- **Streamlit Cloud**: nová app, prepoj Git repo, vyber `app_streamlit.py` a pridaj `requirements.txt`.
- **Hugging Face Spaces**: vytvor Space (Streamlit), nahraj tieto súbory, definuj `requirements.txt`.
- **VPS**: spusti Docker príkazy vyššie a daj nad to reverzný proxy (napr. Nginx) na vlastnej doméne.
