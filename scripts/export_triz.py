import os
import json
import pandas as pd

# Ищем файлы в текущей директории
file_3d = '3_d _1.xlsx'
file_matrix = 'Матриця суперечностей ТРВЗ для муніципального управління.xlsx'
file_spheres = 'Матриця ТРВЗ_ Сфери, Параметри та Принципи Вирішення Конфліктів.xlsx'
file_registry = 'Реєстр принципів ТРИЗ та шаблонів рішень.xlsx'

# Считываем данные (с приоритетом сводного файла 3_d _1.xlsx)
if os.path.exists(file_3d):
    xls = pd.ExcelFile(file_3d)
    df_matrix = pd.read_excel(file_3d, sheet_name=xls.sheet_names[0])
    df_registry = pd.read_excel(file_3d, sheet_name=xls.sheet_names[1])
    df_spheres = pd.read_excel(file_3d, sheet_name=xls.sheet_names[2])
else:
    df_matrix = pd.read_excel(file_matrix)
    df_registry = pd.read_excel(file_registry)
    df_spheres = pd.read_excel(file_spheres)

# Очистка и нормализация колонок
triz_data = {
    "spheres": df_spheres[['Domain', 'Keyword', 'Improving', 'Worsening']].to_dict(orient='records'),
    "matrix": df_matrix[['improving', 'worsening', 'principles']].to_dict(orient='records'),
    "principles": df_registry[['id', 'Назва принципу', 'Суть для громади', 'template', 'Приклад застосування']].to_dict(orient='records')
}

# Сохраняем в JSON для Django
os.makedirs('hostui', exist_ok=True)
output_path = os.path.join('hostui', 'triz_data.json')

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(triz_data, f, ensure_ascii=False, indent=2)

print(f" Успешно заэкспортировано {len(triz_data['spheres'])} сфер, {len(triz_data['matrix'])} строк матрицы и {len(triz_data['principles'])} шаблонов в {output_path}")
