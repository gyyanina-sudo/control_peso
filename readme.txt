Voy a crear una app Flask desde cero en este proyecto para registrar pesos de una persona (alta de registros y listado/historial). Primero reviso la carpeta actual y luego genero la estructura mínima funcionando.

La carpeta está vacía, así que voy a crear los archivos base: app.py, una plantilla HTML y requirements.txt, con almacenamiento simple en pesos.json para que puedas usarla enseguida.

Ya dejé la app armada; ahora voy a validar rápidamente que no haya errores de sintaxis/linter y te paso cómo ejecutarla.

Listo: te creé una aplicación Flask funcional para registrar el peso de una persona.

Archivos creados
app.py
templates/index.html
requirements.txt
Qué hace
Formulario para cargar:
nombre
peso (kg)
fecha (opcional)
Guarda cada registro en pesos.json.
Muestra historial de registros en una tabla (más recientes arriba).
Cómo ejecutarla
En la carpeta del proyecto (d:\Cursor con Python\control_peso):

Instalar dependencias:
pip install -r requirements.txt
Ejecutar la app:
python app.py
Abrir en el navegador:
http://127.0.0.1:5000
Si querés, en el siguiente paso te la mejoro con:

edición/eliminación de registros,
gráfico de evolución del peso,
y base de datos SQLite en vez de JSON.