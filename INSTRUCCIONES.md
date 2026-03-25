# 🚀 Talk With Victor — Instrucciones de lanzamiento

## ¿Qué tienes aquí?

Una aplicación web completa con:
- ✅ Página de marketing (index.html)
- ✅ Login para alumnos
- ✅ Biblioteca de vídeos (subida directa + YouTube)
- ✅ Panel personal de cada alumno
- ✅ Sección de correcciones de textos
- ✅ Panel de administrador completo (gestión de alumnos, vídeos, correcciones)
- ✅ Integración con Stripe para pagos
- ✅ Base de datos SQLite (sin configuración)

---

## PASO 1 — Probar en tu ordenador (5 min)

1. Instala Python desde python.org si no lo tienes
2. Abre la terminal en la carpeta del proyecto
3. Ejecuta:
   ```
   pip install -r requirements.txt
   python app.py
   ```
4. Abre tu navegador en: **http://localhost:5000**
5. Entra en `/login` con:
   - Email: `victor9232005@gmail.com`
   - Contraseña: `changeme123`

---

## PASO 2 — Subir a internet con Render (gratis)

### 2a) GitHub
1. Ve a **github.com** y crea una cuenta gratis
2. Crea un repositorio nuevo llamado `talkwithvictor`
3. Sube todos los archivos (puedes arrastrarlos en la web)

### 2b) Render
1. Ve a **render.com** y crea cuenta (puedes entrar con GitHub)
2. Haz clic en "New Web Service"
3. Conecta tu repositorio de GitHub
4. Render detectará el `render.yaml` automáticamente
5. Haz clic en "Create Web Service"

Tu app estará en: `https://talkwithvictor.onrender.com`

### 2c) Variables de entorno en Render
En el panel de Render → Environment, añade:

| Variable | Valor |
|----------|-------|
| `ADMIN_EMAIL` | victor9232005@gmail.com |
| `ADMIN_PASSWORD` | (tu contraseña segura) |
| `APP_URL` | https://talkwithvictor.onrender.com |

---

## PASO 3 — Configurar Stripe (cuando quieras cobrar)

1. Ve a **stripe.com** y crea cuenta gratis
2. Dashboard → Developers → API Keys
3. Copia la "Secret key" (`sk_live_...`)
4. En Render → Environment añade: `STRIPE_SECRET_KEY`

### Crear los productos en Stripe:
1. Products → Add product
2. Crea "Matrícula" — precio único €50
3. Crea "Mensualidad" — precio recurrente €35/mes
4. Copia los Price IDs (empiezan por `price_...`) y añádelos:
   - `STRIPE_ENROLLMENT_PRICE`
   - `STRIPE_MONTHLY_PRICE`

---

## CÓMO USAR EL PANEL DE ADMIN

Accede en `/login` con tu email y contraseña.

### Añadir un alumno:
1. Admin → Alumnos → Nuevo alumno
2. Rellena nombre, email, contraseña, nivel
3. Activa la membresía si ya pagó
4. Envíale el email y contraseña manualmente

### Subir un vídeo:
**Opción A — Archivo directo:**
1. Admin → Vídeos → Subir vídeo
2. Rellena título, categoría, nivel
3. Selecciona o arrastra el archivo de vídeo (MP4, MOV...)
4. Haz clic en "Publicar vídeo"

**Opción B — YouTube (sin ocupar espacio):**
1. Sube el vídeo a YouTube en modo "No listado"
2. Copia la URL: `https://www.youtube.com/watch?v=ABC123`
3. Cámbiala a formato embed: `https://www.youtube.com/embed/ABC123`
4. En Admin → Vídeos → Subir vídeo, pega la URL

### Corregir textos de alumnos:
1. Admin → Correcciones
2. Haz clic en "Corregir →" para cada texto pendiente
3. Escribe tu corrección y guarda

---

## ⚠️ IMPORTANTE: Almacenamiento de vídeos

Si subes vídeos directamente al servidor **en Render plan gratuito**, los archivos se borran cuando el servidor se reinicia. Para vídeos permanentes tienes dos opciones:

**Opción A — YouTube (gratis, recomendado):**
Usa el modo "No listado" — los vídeos no aparecen en búsquedas pero solo tus alumnos pueden verlos (tienen la URL embed).

**Opción B — Cloudinary (gratis hasta 25GB):**
1. Crea cuenta en cloudinary.com
2. Sube tus vídeos ahí
3. Usa la URL que te da Cloudinary en el campo de YouTube/URL

**Opción C — Servidor de pago:**
En Render, el plan Starter (€7/mes) tiene disco persistente.

---

## Preguntas frecuentes

**¿Cuánto cuesta todo?**
- Render: Gratis para empezar
- Stripe: Gratis (solo cobra ~1.5% por transacción)
- Dominio propio: ~€12/año en namecheap.com (opcional)

**¿Puedo usar mi dominio (talkwithvictor.com)?**
Sí. Compra el dominio en namecheap.com y conéctalo en Render → Settings → Custom Domain.

---

*Creado con Claude para Talk With Victor · 2026*
