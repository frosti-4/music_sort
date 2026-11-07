import os
import argparse
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from mutagen.asf import ASF
from mutagen.id3 import ID3NoHeaderError, ID3
from mutagen import MutagenError

# Максимум потоков сканирования (подстраивается под число ядер CPU)
_scanner_lock = threading.Lock()
_NUM_THREADS = None


def _get_num_threads():
    """Возвращает оптимальное число потоков для сканирования."""
    global _NUM_THREADS
    if _NUM_THREADS is None:
        _NUM_THREADS = os.cpu_count() or 1
    return _NUM_THREADS

def get_audio_info(file_path):
    """
    Извлекает и возвращает метаданные из аудиофайла.
    Поддерживает MP3, FLAC, Ogg Vorbis, M4A/MP4, WMA.
    """
    info = {
        "Название файла": os.path.basename(file_path),
        "Путь к файлу": file_path,
        "Директория": os.path.dirname(os.path.abspath(file_path)),
        "Исполнитель": "Неизвестно",
        "Название": "Неизвестно",
        "Альбом": "Неизвестно",
        "Жанр": "Неизвестно",
        "Год": "Неизвестно",
        "Длительность (сек)": "Неизвестно",
        "Тип файла": "Неизвестно",
        "Ошибка": None
    }

    try:
        audio = None
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == '.mp3':
            audio = MP3(file_path)
            info["Тип файла"] = ".mp3"
        elif file_extension == '.flac':
            audio = FLAC(file_path)
            info["Тип файла"] = ".flac"
        elif file_extension in ('.ogg', '.oga'):
            audio = OggVorbis(file_path)
            info["Тип файла"] = ".ogg"
        elif file_extension == '.mp4':
            audio = MP4(file_path)
            info["Тип файла"] = '.mp4'
        elif file_extension in ('.m4a', '.mp4'):
            audio = MP4(file_path)
            info["Тип файла"] = '.m4a'
        elif file_extension == '.wma':
            audio = ASF(file_path)
            info["Тип файл"] = ".wma"
        else:
            info["Ошибка"] = "Неподдерживаемый формат аудиофайла."
            return info

        if audio and audio.info:
            info["Длительность (сек)"] = int(audio.info.length)

        if audio and audio.tags:
            if file_extension == '.mp3':
                if 'TPE1' in audio.tags:
                    info["Исполнитель"] = str(audio.tags['TPE1'])
                if 'TIT2' in audio.tags:
                    info["Название"] = str(audio.tags['TIT2'])
                if 'TALB' in audio.tags:
                    info["Альбом"] = str(audio.tags['TALB'])
                if 'TCON' in audio.tags:
                    info["Жанр"] = str(audio.tags['TCON'])
                if 'TDRC' in audio.tags:
                    info["Год"] = str(audio.tags['TDRC'])
                elif 'TYER' in audio.tags:
                    info["Год"] = str(audio.tags['TYER'])
            elif file_extension in ['.flac', '.ogg', '.oga']:
                if 'artist' in audio.tags:
                    info["Исполнитель"] = ", ".join(audio.tags['artist'])
                if 'title' in audio.tags:
                    info["Название"] = ", ".join(audio.tags['title'])
                if 'album' in audio.tags:
                    info["Альбом"] = ", ".join(audio.tags['album'])
                if 'genre' in audio.tags:
                    info["Жанр"] = ", ".join(audio.tags['genre'])
                if 'date' in audio.tags:
                    info["Год"] = ", ".join(audio.tags['date'])
            elif file_extension == '.mp4':
                if '\xa9ART' in audio.tags:
                    info["Исполнитель"] = audio.tags['\xa9ART'][0]
                if '\xa9nam' in audio.tags:
                    info["Название"] = audio.tags['\xa9nam'][0]
                if '\xa9alb' in audio.tags:
                    info["Альбом"] = audio.tags['\xa9alb'][0]
                if '\xa9gen' in audio.tags:
                    info["Жанр"] = audio.tags['\xa9gen'][0]
                if '\xa9day' in audio.tags:
                    info["Год"] = audio.tags['\xa9day'][0]
            elif file_extension == '.wma':
                if 'Author' in audio.tags:
                    info["Исполнитель"] = audio.tags['Author'][0].value
                if 'Title' in audio.tags:
                    info["Название"] = audio.tags['Title'][0].value
                if 'WM/AlbumTitle' in audio.tags:
                    info["Альбом"] = audio.tags['WM/AlbumTitle'][0].value
                if 'WM/Genre' in audio.tags:
                    info["Жанр"] = audio.tags['WM/Genre'][0].value
                if 'WM/Year' in audio.tags:
                    info["Год"] = audio.tags['WM/Year'][0].value

    except ID3NoHeaderError:
        info["Ошибка"] = "MP3 файл без ID3 тегов."
    except MutagenError as e:
        info["Ошибка"] = f"Ошибка чтения метаданных: {e}"
    except Exception as e:
        info["Ошибка"] = f"Неизвестная ошибка: {e}"

    return info

def get_unique_artists(audio_files_info):
    """
    Собирает и возвращает список всех уникальных исполнителей, найденных в предоставленных данных.
    """
    artists = set()
    for info in audio_files_info:
        artist = info.get("Исполнитель")
        if artist and artist != "Неизвестно":
            # Разделяем исполнителей, если они перечислены через запятую
            # и добавляем каждого в набор
            for a in [s.strip() for s in artist.split(',')]:
                if a:
                    artists.add(a)
    return sorted(list(artists))

def list_all_artists(artists_list):
    """
    Выводит список всех уникальных исполнителей.
    """
    if artists_list:
        print("\n--- Список всех исполнителей ---")
        for artist in artists_list:
            print(f"- {artist}")
        print("-" * 30)
    else:
        print("\nИсполнители не найдены в отсканированных аудиофайлах.")


def sanitize_filename(name):
    """Удаляет недопустимые символы из имени файла/папки."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.replace(' ', '_')

def rename(files, output_dir):
    """Переименовывает файлы в формате 'Название-Исполнитель'."""
    print(f"\n--- Переименование треков ---")
    renamed_count = 0

    for info in files:
        artist = info.get("Исполнитель") or "Неизвестно"
        name = info.get("Название") or "Неизвестно"
        path = info.get("Путь к файлу")
        ext = info.get("Тип файла")
        direct = info.get("Директория")

        if path and not os.path.exists(path):
            print(f"Пропущено '{info.get('Название файла')}': файл не найден.")
            continue

        artist = sanitize_filename(artist)
        name = sanitize_filename(name)

        if name != "Неизвестно" or artist != "Неизвестно":
            source = path
            dest = os.path.join(direct, f"{name}-{artist}{ext}")
            if dest != source:
                print(f"Переименовано: {path}")
                os.rename(source, dest)
                info["Путь к файлу"] = dest
                renamed_count += 1
            else:
                print(f"Пропущено '{info.get('Название файла')}' (уже в нужном имени).")
        else:
            print(f"Пропущено '{info.get('Название файла')}': неизвестно название или исполнитель.")

    print(f"\nПереименовано файлов: {renamed_count}")
    print("-" * 30)


def organize_by_artist(files, base_output_directory):
    """
    Создает папки для исполнителей и перемещает в них соответствующие треки.
    """
    print(f"\n--- Организация треков по исполнителям в директории: {base_output_directory} ---")

    os.makedirs(base_output_directory, exist_ok=True)

    moved_count = 0
    for info in files:
        artist = info.get("Исполнитель")
        original_path = info.get("Путь к файлу")
        file_name = info.get("Название файла")

        if not (artist and artist != "Неизвестно"):
            print(f"Пропущено '{file_name}': Неизвестный исполнитель.")
            continue
        if not original_path or not os.path.exists(original_path):
            print(f"Пропущено '{file_name}': файл не найден или путь некорректен: {original_path}")
            continue

        main_artist = artist.split(',')[0].strip()
        main_artist = sanitize_filename(main_artist)

        artist_folder_path = os.path.join(base_output_directory, main_artist)
        os.makedirs(artist_folder_path, exist_ok=True)

        destination_path = os.path.join(artist_folder_path, file_name)

        try:
            if os.path.abspath(original_path) == os.path.abspath(destination_path):
                print(f"Файл '{file_name}' уже находится в целевой директории '{artist_folder_path}'. Пропущено.")
                continue

            shutil.move(original_path, destination_path)
            print(f"Перемещено: '{file_name}' из '{os.path.dirname(original_path)}' в '{artist_folder_path}'")
            info["Путь к файлу"] = destination_path
            moved_count += 1
        except shutil.Error as e:
            print(f"Ошибка при перемещении файла '{file_name}': {e}")
        except Exception as e:
            print(f"Неизвестная ошибка при перемещении файла '{file_name}': {e}")

    if moved_count > 0:
        print(f"\nУспешно перемещено {moved_count} треков.")
    else:
        print("\nТреки для перемещения не найдены или все уже находятся в нужных папках.")
    print("-" * 30)

def main():
    """
    Основная функция для сканирования указанной директории,
    вывода информации об аудиофайлах, списка исполнителей,
    и организации треков по папкам исполнителей.
    """
    parser = argparse.ArgumentParser(
        description="Сканирует аудиофайлы в указанной директории, выводит их метаданные и список исполнителей. Может также организовывать треки по папкам исполнителей."
    )

    parser.add_argument(
        "-i", "--input-dir",
        type=str,
        default=os.getcwd(),
        help="Путь к директории для сканирования (по умолчанию: текущая директория)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        help="Базовая директория, куда будут перемещены треки в папки исполнителей. Если не указана, используется --input-dir."
    )
    parser.add_argument(
        "-s", "--sort",
        action="store_true",
        help="Сортировка треков по папкам исполнителей."
    )
    parser.add_argument(
        "-r", "--rename",
        action="store_true",
        help="Переименование файлов в формате название-исполнитель"
    )

    args = parser.parse_args()

    scan_directory = args.input_dir
    base_output_directory = args.output_dir if args.output_dir else scan_directory

    if not os.path.isdir(scan_directory):
        print(f"Ошибка: Директория для сканирования '{scan_directory}' не найдена или не является директорией.")
        return

    print(f"Сканирование директории: {scan_directory} и всех поддиректорий...\n")

    audio_extensions = ('.mp3', '.flac', '.ogg', '.oga', '.m4a', '.mp4', '.wma')
    all_audio_info = []
    found_audio_files = False

    # --- 1. Сканирование файлов ---
    files_to_scan = []
    for root, dirs, files in os.walk(scan_directory):
        for item in files:
            file_path = os.path.join(root, item)
            if item.lower().endswith(audio_extensions):
                files_to_scan.append(file_path)
                found_audio_files = True

    if found_audio_files:
        # --- 2. Параллельное извлечение метаданных ---
        print(f"Найдено {len(files_to_scan)} аудиофайлов. Извлекаю метаданные...\n")
        with ThreadPoolExecutor(max_workers=_get_num_threads()) as executor:
            for info in executor.map(get_audio_info, files_to_scan):
                all_audio_info.append(info)

        # --- 3. Вывод информации о каждом файле (если не сортировка/переименование) ---
        if not args.sort and not args.rename:
            for info in all_audio_info:
                print(f"--- Информация о файле: {info.get('Путь к файлу')} ---")
                for key, value in info.items():
                    print(f"  {key}: {value}")
                print("-" * 30)

        # --- 4. Переименование ---
        if args.rename:
            rename(all_audio_info, base_output_directory)

        # --- 5. Сортировка по исполнителям ---
        if args.sort:
            organize_by_artist(all_audio_info, base_output_directory)
    else:
        print("Аудиофайлы не найдены в указанной директории или ее поддиректориях.")
        print("Убедитесь, что в этой директории или ее поддиректориях есть файлы с расширениями:")
        print(f"{', '.join(audio_extensions)}")
        print("Или поместите несколько аудиофайлов для тестирования.")

    # --- 6. Список всех исполнителей ---
    artists_list = get_unique_artists(all_audio_info)
    list_all_artists(artists_list)

if __name__ == "__main__":
    main()
