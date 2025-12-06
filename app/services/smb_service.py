"""SMB сервис для работы с сетевыми папками"""
import io
from smb.SMBConnection import SMBConnection
from flask import current_app


class SMBService:
    """Сервис для работы с SMB шарами"""

    def __init__(self, host=None, port=None, username=None, password=None, share=None):
        self.host = host or current_app.config['SMB_HOST']
        self.port = port or current_app.config['SMB_PORT']
        self.username = username or current_app.config['SMB_USER']
        self.password = password or current_app.config['SMB_PASSWORD']
        self.share = share or current_app.config['SMB_SHARE']
        self.conn = None

    def connect(self):
        """Установить соединение с SMB сервером"""
        self.conn = SMBConnection(
            self.username,
            self.password,
            'client',
            'server',
            use_ntlm_v2=True,
            is_direct_tcp=True
        )
        return self.conn.connect(self.host, self.port)

    def disconnect(self):
        """Закрыть соединение"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def list_files(self, path):
        """Получить список файлов в папке"""
        if not self.conn:
            self.connect()

        files = []
        for f in self.conn.listPath(self.share, path):
            if not f.filename.startswith('.'):
                files.append({
                    'filename': f.filename,
                    'is_directory': f.isDirectory,
                    'size': f.file_size,
                    'create_time': f.create_time
                })
        return files

    def create_directory(self, path):
        """Создать папку"""
        if not self.conn:
            self.connect()

        self.conn.createDirectory(self.share, path)

    def save_file(self, path, data):
        """Сохранить файл на SMB шару

        Args:
            path: Путь к файлу на шаре
            data: bytes или BytesIO объект
        """
        if not self.conn:
            self.connect()

        if isinstance(data, bytes):
            file_obj = io.BytesIO(data)
        else:
            file_obj = data
            file_obj.seek(0)

        self.conn.storeFile(self.share, path, file_obj)

    def read_file(self, path):
        """Прочитать файл с SMB шары

        Returns:
            BytesIO объект с содержимым файла
        """
        if not self.conn:
            self.connect()

        file_obj = io.BytesIO()
        self.conn.retrieveFile(self.share, path, file_obj)
        file_obj.seek(0)
        return file_obj

    def file_exists(self, path):
        """Проверить существование файла"""
        if not self.conn:
            self.connect()

        try:
            # Получаем имя файла и путь к папке
            parts = path.rsplit('/', 1)
            if len(parts) == 2:
                folder, filename = parts
            else:
                folder = ''
                filename = parts[0]

            files = self.conn.listPath(self.share, folder)
            for f in files:
                if f.filename == filename:
                    return True
            return False
        except Exception:
            return False

    def directory_exists(self, path):
        """Проверить существование папки"""
        if not self.conn:
            self.connect()

        try:
            self.conn.listPath(self.share, path)
            return True
        except Exception:
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
