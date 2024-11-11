import os
import pandas as pd
from fpdf import FPDF
from collections import defaultdict
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PDF_FOLDER'] = 'pdfs'
app.secret_key = 'supersecretkey'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)

# Function to categorize players based on age, weight, and gender
def categorize_player(age, weight, gender):
    gender = str(gender).strip().upper()
    if gender not in ['MALE', 'FEMALE']:
        return "Uncategorized"

    try:
        age = int(age)
        weight = float(weight)
    except ValueError:
        return "Uncategorized"

    categories = {
        # Add your categorization logic here
        # This can include various weight and age categories as needed
    }

    if age < 14:
        age_category = str(age)
    elif 14 <= age <= 15:
        age_category = f"14-15 {gender}"
    elif 16 <= age <= 17:
        age_category = f"16-17 {gender}"
    else:
        age_category = f"18+ {gender}"

    if age_category in categories:
        for category, max_weight in categories[age_category].items():
            if weight <= max_weight:
                return f"{age_category} {category}"

    return "Uncategorized"

# Function to create groups of 4 players with specific matchup rules
def create_groups(players):
    groups = []
    players_copy = players.copy()
    
    while len(players_copy) > 0:
        group = players_copy[:4]
        if len(group) == 4:
            player1, player2, player3, player4 = group
            if (player1['state'] == player2['state'] and player3['state'] == player4['state']) or \
               (player1['club'] == player2['club'] and player3['club'] == player4['club']):
                group[1], group[3] = group[3], group[1]
        
        groups.append(group)
        players_copy = players_copy[4:]
        
    return groups

# Function to read the Excel file and return player data
def read_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        required_columns = ['name', 'age', 'weight', 'gender', 'club', 'city', 'state']
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Excel file is missing one or more required columns.")
        players = df.to_dict(orient='records')
        return players
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return []

# Function to generate a PDF with categorized players
def generate_pdf(categories, output_file, logo_path, tournament_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for category, players in categories.items():
        groups = create_groups(players)
        for group_index, group in enumerate(groups, start=1):
            pdf.add_page()

            # Add logo
            pdf.image(logo_path, x=10, y=8, w=33)
            
            # Add tournament title
            pdf.set_font("Arial", "B", 20)
            pdf.cell(0, 10, tournament_name, ln=True, align="C")
            
            # Add pool name and category
            pdf.set_font("Arial", "B", 16)
            pool_name = f"{category} - Group {group_index}"
            pdf.cell(0, 10, pool_name, ln=True, align="C")
            
            # Add table header without the state column
            pdf.set_font("Arial", "B", 12)
            pdf.ln(10)
            pdf.cell(10, 10, "No.", 1)
            pdf.cell(40, 10, "Name", 1)
            pdf.cell(20, 10, "Age", 1)
            pdf.cell(30, 10, "Weight (kg)", 1)
            pdf.cell(70, 10, "Club", 1)
            pdf.cell(30, 10, "City", 1)
            pdf.ln()

            # Add player information in the table
            pdf.set_font("Arial", "", 12)
            for index, player in enumerate(group, start=1):
                pdf.cell(10, 10, str(index), 1)
                pdf.cell(40, 10, player['name'], 1)
                pdf.cell(20, 10, str(int(player['age'])), 1)
                pdf.cell(30, 10, str(player['weight']), 1)
                pdf.cell(70, 10, player['club'], 1)
                pdf.cell(30, 10, str(player.get('city', '')), 1)
                pdf.ln()

            # Add placeholders for winner and match outcomes
            pdf.ln(25)
            pdf.cell(0, 10, "Winner name: _______________________", ln=True)
            pdf.ln(5)
            pdf.cell(0, 10, "1) ___________________________", ln=True)
            pdf.cell(0, 10, "2) ___________________________", ln=True)
            pdf.cell(0, 10, "3) ___________________________", ln=True)
            pdf.cell(0, 10, "4) ___________________________", ln=True)

    pdf.output(output_file)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        tournament_name = request.form['tournament_name']
        excel_file = request.files['excel_file']
        logo_file = request.files['logo_file']
        
        if excel_file and logo_file:
            excel_filename = secure_filename(excel_file.filename)
            logo_filename = secure_filename(logo_file.filename)
            excel_path = os.path.join(app.config['UPLOAD_FOLDER'], excel_filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
            excel_file.save(excel_path)
            logo_file.save(logo_path)
            
            players = read_excel(excel_path)
            if not players:
                flash("Invalid Excel file.")
                return redirect(request.url)
            
            categories = defaultdict(list)
            for player in players:
                category = categorize_player(player.get("age"), player.get("weight"), player.get("gender"))
                categories[category].append(player)
            
            output_file = os.path.join(app.config['PDF_FOLDER'], 'players_report.pdf')
            generate_pdf(categories, output_file, logo_path, tournament_name)
            
            return send_file(output_file, as_attachment=True)
        else:
            flash("Please upload both Excel and logo files.")
            return redirect(request.url)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
