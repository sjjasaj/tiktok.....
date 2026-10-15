# TikTok Gift Controller — prototipo Windows

## Obtener el EXE sin instalar Python en tu PC
Este proyecto incluye un flujo de GitHub Actions que compila la aplicación en un equipo Windows en la nube. No necesitas instalar Python localmente.

1. Inicia sesión o crea una cuenta en GitHub.
2. Crea un repositorio nuevo.
3. Descomprime este ZIP y sube **todos los archivos y carpetas** al repositorio (incluida `.github/workflows/build-windows.yml`).
4. Abre la pestaña **Actions** del repositorio y selecciona **Build Windows EXE**.
5. Pulsa **Run workflow** si no comenzó automáticamente al subir los archivos.
6. Cuando termine correctamente, abre la ejecución y descarga el artefacto **TikTokGiftController-Windows**.
7. Descomprime el artefacto y ejecuta `TikTokGiftController.exe`.

GitHub puede pedirte habilitar Actions. El archivo descargado es portable: no instala Python en tu PC ni crea servicios de inicio automático. Windows puede mostrar una advertencia de SmartScreen porque el ejecutable no está firmado digitalmente.

## Incluye
- Panel de conexión por usuario de TikTok LIVE
- Registro de regalos detectados
- Reglas por nombre de regalo
- Notificación y sonido de Windows
- Prueba local sin conectar a TikTok
- Botón para desconectar

## Limitaciones
La conexión usa `TikTokLive`, una biblioteca comunitaria no oficial. TikTok puede cambiar su sistema y romper la conexión. La app no pide ni debe recibir tu contraseña de TikTok. Este prototipo todavía necesita probarse con un LIVE real.
