import argparse
import os
import zipfile
import json
from docx import Document
from pathlib import Path
from io import BytesIO
from datetime import datetime
from collections.abc import MutableMapping

def check_path(path):

    path = Path(path)
    
    if not path.exists():
        print(f"Ошибка: Путь '{path}' не существует")
        return False
    
    return True

def check_report(report):
    
    path = Path(report)

    if not path.exists():
        print(f"Ошибка: Путь '{path}' не существует")
        return False
    
    if path.is_dir():
        print(f"Ошибка: '{path}' не является файлом")
        return False
    
    # Проверяем расширение файла
    allowed_extensions = {
        '.docx': 'Word документ',
        # '.xlsx': 'Excel таблица', 
        # '.pdf': 'PDF документ',
        # '.csv': 'CSV файл',
        '.json': 'JSON файл'
    }
    
    extension = path.suffix.lower()
    
    if not extension:
        print(f"Ошибка: Файл '{path}' не имеет расширения")
        return False
    
    if extension not in allowed_extensions:
        print(f"Ошибка: Расширение '{extension}' не поддерживается")
        return False
    
    return True

def zip_tree(zip, structure):   
    with zip as zipf:
        # Получаем файлы и папки
        for file_info in zipf.infolist():
            path = Path(file_info.filename)
            extension = path.suffix.lower()  
            path_parts = path.parts
            
            # Построение дерева
            current_level = structure
            
            # переход на узел (папку)
            for i, part in enumerate(path_parts):
                if i < len(path_parts)-1:
                    key = f"{'dir'}_{part}"
                    current_level = current_level[key]
            
            # создание узла (папки) или файла
            if file_info.is_dir():
                key = f"{'dir'}_{part}"
                current_level[key] = { 
                                       "name": part,
                                       "type": "folder",
                                       "size": file_info.file_size,
                                       "modif_date": datetime(*file_info.date_time).strftime("%Y-%m-%d %H:%M:%S")
                                     }
            else:
                # если этой zip обрабатываем его
                if extension == '.zip':
                    key = f"{'zip'}_{part}"
                    zfiledata = BytesIO(zipf.read(part))
                    current_level[key] = zip_tree(
                        zipfile.ZipFile(zfiledata),
                        { 
                            "name": part,
                            "type": "zip",
                            "size": file_info.file_size,
                            "modif_date": datetime(*file_info.date_time).strftime("%Y-%m-%d %H:%M:%S")
                        }
                    )
                else:
                # файл
                    key = f"{'fol'}_{part}"
                    current_level[key] = { 
                                           "name": part,
                                           "type": "file",
                                           "size": file_info.file_size,
                                           "modif_date": datetime(*file_info.date_time).strftime("%Y-%m-%d %H:%M:%S")
                                        }

    return structure

def folder_tree(path):
    structure = {}

    path = Path(path)
    
    # Получаем все файлы и папки
    for file_path in path.rglob('*'):
        extension = file_path.suffix.lower() 
        relative_path = file_path.relative_to(path)
        path_parts = relative_path.parts

        # Построение дерева
        current_level = structure

        # переход на узел (папку)
        for i, part in enumerate(path_parts):
            if i < len(path_parts)-1:
                key = f"{'dir'}_{part}"
                current_level = current_level[key]

        # создание узла (папки) или файла
        if file_path.is_dir():
            key = f"{'dir'}_{part}"
            current_level[key] = { 
                                   "name": part,
                                   "type": "folder",
                                   "size": file_path.stat().st_size,
                                   "modif_date": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                                 }
        else:
            # если этой zip обрабатываем его
            if extension == '.zip':
                key = f"{'zip'}_{part}"
                
                current_level[key] = zip_tree( 
                    zipfile.ZipFile(file_path, 'r'),
                    { 
                        "name": part,
                        "type": "zip",
                        "size": file_path.stat().st_size,
                        "modif_date": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
            else:
            # файл
                key = f"{'fol'}_{part}"
                current_level[key] = { 
                                       "name": part,
                                       "type": "file",
                                       "size": file_path.stat().st_size,
                                       "modif_date": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                                     }
    
    return structure

def tree_to_strings(data, prefix="", is_root=True, str=[]):
    """
    Рекурсивно переводим дерево в список строк
    """
    # Определяем иконки для разных типов (в .Doc не записывает иконку)
    icons = {
        "folder": "📁",
        "file":   "📄",
        "zip":    "📦"
    }

    if is_root:
        str.append(f"{icons['folder']} /")
        is_root = False
    
    # сортируем (папки сначала, затем файлы)
    items = []
    for key, value in data.items():
        items.append((key, value))
    
    # cортируем: сначала папки, потом файлы
    items.sort(key=lambda x: (0 if x[1].get('type') == 'folder' or x[1].get('type') == 'zip' else 1, x[0]))
    
    # Обрабатываем каждый элемент
    for i, (key, value) in enumerate(items): 
        prefix_tmp = "      "       
        current_prefix = prefix + prefix_tmp
        
        
        # Получаем иконку для типа
        item_type = value.get('type', 'file')
        icon = icons.get(item_type, '@')
        
        # Форматируем размер
        size = value.get('size', 0)
        size_str = f"{size} bytes"
        
        # Форматируем дату
        modif_date = value.get('modif_date', '')
        try:
            date_obj = datetime.strptime(modif_date, '%Y-%m-%d %H:%M:%S')
            date_str = date_obj.strftime('%d.%m.%Y %H:%M')
        except:
            date_str = modif_date
        
        # Выводим текущий элемент
        str.append(f"{prefix}{prefix_tmp}{icon} {value.get('name', key)} ({value.get('type', '')}/{size_str}/{date_str})")
        
        # Рекурсивно обрабатываем вложенные элементы (для папок)
        if ( item_type == 'folder' or item_type == 'zip' ):
            # Ищем вложенные элементы
            nested_data = {}
            for k, v in value.items():
                if k not in ['name', 'type', 'size', 'modif_date']:
                    nested_data[k] = v
            
            if nested_data:
                tree_to_strings(nested_data, current_prefix, False, str)

def save_doc(tree,file):
    str = []
    tree_to_strings(data=tree, is_root=True, str=str)

    doc = Document()
    doc.add_heading("Пример .DOCS", 0)
    for v in str:
        doc.add_paragraph(v)
    doc.save(file)

def save_json(tree, file):
    with open(file, 'w', encoding='utf-8') as f:
        json_output = json.dumps(tree, indent=2, ensure_ascii=False)
        f.write(json_output)

def main():
    parser = argparse.ArgumentParser(description='Анализ структуры файлов и папок')
    parser.add_argument('--path', type=str, required=True, 
                       help='Путь к анализируемой папке ')
    
    parser.add_argument('--report', type=str, required=True, 
                       help=' Путь к отчету')
    
    args = parser.parse_args()

    # args.path = '/home/user/dev/python/project/python-project6/folder_first'
    # args.report = '/home/user/dev/python/project/python-project6/report/test.json'

    if not check_path(args.path):
        return
    
    if not check_report(args.report):
        return
    
    tree = folder_tree(args.path)  

    path = Path(args.report)
    extension = path.suffix.lower()

    if extension == ".docx":
        save_doc(tree, args.report)
    elif extension == ".json":
        save_json(tree, args.report)
    elif extension == ".pdf":
        pass
    elif extension == ".xlsx":
        pass
    elif extension == ".csv":
        pass
        
if __name__ == "__main__":
    main()