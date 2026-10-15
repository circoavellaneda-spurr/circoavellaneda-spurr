import os
import sys
import unicodedata
from flask import Flask, render_template, request
import webbrowser
from threading import Thread
import pandas as pd
import requests
from io import BytesIO

def get_resource_path(relative_path):
    """
    Detecta si la aplicación corre como EXE o como script normal.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Inicializamos Flask
app = Flask(__name__, template_folder=get_resource_path('templates'),
            static_folder=get_resource_path('static'))

def normalizar_texto(texto):
    """
    Normaliza un texto para poder comparar nombres de talleres
    ignorando mayúsculas, minúsculas y acentos.
    """

    texto = str(texto).strip().upper()

    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

    return texto

def actualizacion(taller):
    url = (
        "https://docs.google.com/spreadsheets/d/"
        "1RdujC_8qulG31eoikSco4Ikh9zGTfibtsEuLb-m_oLM/"
        "export?format=xlsx")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(
            f"No se pudo descargar el archivo de Google Sheets: {e}"
        )
    excel_file = pd.ExcelFile(BytesIO(response.content))
    objetivo = normalizar_texto(taller)

    # Mostrar en consola las hojas disponibles
    print("\nHojas encontradas:")
    for hoja in excel_file.sheet_names:
        print(" -", hoja)

    # Buscar la hoja
    for hoja in excel_file.sheet_names:
        hoja_normalizada = normalizar_texto(hoja)
        if objetivo in hoja_normalizada:
            print(f"\nTaller encontrado: {hoja}")
            df = pd.read_excel(
                excel_file,
                sheet_name=hoja,
                header=0
            )
            # Reemplazar NaN por texto vacío
            df = df.fillna("")
            return df

    raise ValueError(
        f"No se encuentra el taller '{taller}'.")

def cargar_datos_lista(df):

    df = df.dropna(how='all')

    # Convertir NaN a vacío
    df = df.fillna('')

    # Eliminar filas sin apellido Y sin nombre
    if 'APELLIDOS' in df.columns and 'NOMBRES' in df.columns:

        df = df[
            (df['APELLIDOS'].astype(str).str.strip() != '') |
            (df['NOMBRES'].astype(str).str.strip() != '')
        ]

    return df.to_dict(orient='records')

def buscar_estudiante(dni='', nombre=''):

    url = (
        "https://docs.google.com/spreadsheets/d/"
        "1RdujC_8qulG31eoikSco4Ikh9zGTfibtsEuLb-m_oLM/"
        "export?format=xlsx"
    )
    response = requests.get(
        url,
        timeout=30
    )
    response.raise_for_status()
    excel_file = pd.ExcelFile(
        BytesIO(response.content)
    )
    dni_busqueda = normalizar_texto(dni)
    nombre_busqueda = normalizar_texto(nombre)

    resultados = []

    # RECORRER TODAS LAS HOJAS
    for hoja in excel_file.sheet_names:

        print(f"Buscando en hoja: {hoja}")

        try:
            df = pd.read_excel(
                excel_file,
                sheet_name=hoja,
                header=0
            )

        except Exception as e:
            print(
                f"Error leyendo hoja {hoja}: {e}"
            )
            continue
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')

        # Reemplazar NaN
        df = df.fillna('')

        # RECORRER ALUMNOS
        for _, fila in df.iterrows():

            apellido = normalizar_texto(
                fila.get('APELLIDOS', '')
            )

            nombre_alumno = normalizar_texto(
                fila.get('NOMBRES', '')
            )

            dni_alumno = normalizar_texto(
                fila.get('DNI', '')
            )

            encontrado = False

            # BUSQUEDA POR DNI
            if dni_busqueda:
                if dni_alumno == dni_busqueda:
                    encontrado = True

            # BUSQUEDA POR NOMBRE
            elif nombre_busqueda:
                nombre_completo = (
                    f"{apellido} {nombre_alumno}"
                )
                if nombre_busqueda in nombre_completo:
                    encontrado = True

            # GUARDAR RESULTADO
            if encontrado:
                alumno = fila.to_dict()
                # Agregar la hoja/taller
                alumno['TALLER'] = hoja

                resultados.append(alumno)
    return resultados

# PÁGINAS
@app.route('/')
def principal():
    return render_template('index.html')

@app.route('/buscarestudiante')
def estudiante():
    return render_template('buscar_estudiante.html')

@app.route('/buscar_listados')
def buscar_listados():
    return render_template('buscar_listados.html')

# RESULTADO DEL TALLER
@app.route('/resultado_estudiante', methods=['POST'])
def resultado_estudiante():
    dni = request.form.get('legajo', '').strip()
    nombre = request.form.get('Apellido_y_Nombre', '').strip()

    if not dni and not nombre:
        return render_template(
            'buscar_estudiante.html',
            mensaje='Ingrese un DNI o un apellido y nombre.'
        )

    try:
        resultados = buscar_estudiante(
            dni=dni,
            nombre=nombre
        )

    except Exception as e:
        return render_template(
            'buscar_estudiante.html',
            mensaje=f'Error al buscar: {e}'
        )

    return render_template(
        'resultado_estudiante.html',
        resultados=resultados,
        dni=dni,
        nombre=nombre
    )

# RESULTADO DEL TALLER
@app.route('/resultado_lista', methods=['POST'])
def resultado_lista():

    taller = request.form.get("talleres", "").strip()

    # Validar taller
    if not taller:
        return render_template(
            'buscar_listados.html',
            mensaje="Debe ingresar un taller."
        )

    # Buscar taller
    try:
        df = actualizacion(taller)

    except ValueError as e:

        return render_template(
            'buscar_listados.html',
            mensaje=str(e)
        )

    except Exception as e:

        return render_template(
            'buscar_listados.html',
            mensaje=f"Ocurrió un error: {e}"
        )

    # Obtener alumnos
    estudiantes = cargar_datos_lista(df)

    if not estudiantes:

        return render_template(
            'buscar_listados.html',
            mensaje=f"No se encontraron alumnos para el taller '{taller}'."
        )

    print(
        f"\nSe encontraron {len(estudiantes)} alumnos "
        f"para el taller '{taller}'."
    )

    # Mostrar resultados

    if 'ADUL' in taller:
        return render_template(
                'resultado_listado_adul.html',
                estudiantes=estudiantes,
                taller=taller
            )
    else:
        return render_template(
                'resultado_listado_peq.html',
                estudiantes=estudiantes,
                taller=taller
            )

# CERRAR
@app.route('/cerrar')
def cerrar():

    print("Cerrando servidor...")

    os._exit(0)

def run_flask():

    app.run(
        port=2026,
        debug=True,
        use_reloader=False
    )

if __name__ == '__main__':

    flask_thread = Thread(
        target=run_flask
    )

    flask_thread.start()

    webbrowser.open(
        "http://127.0.0.1:2026"
    )