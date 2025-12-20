import os
import argparse
import shutil
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from mutagen.asf import ASF
from mutagen.id3 import ID3NoHeaderError, ID3
from mutagen import MutagenError

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
        elif file_extension == '.ogg' or file_extension == '.oga':
            audio = OggVorbis(file_path)
            info["Тип файла"] = ".ogg"
        elif file_extension == '.oga':
            audio = OggVorbis(file_path)
            info["Тип файла"] = ".oga"
        elif file_extension == '.mp4':
            audio = MP4(file_path)
            info["Тип файла"] = '.mp4'
        elif file_extension == '.wma':
            audio = ASF(file_path)
            info["Тип файла"] = ".wma"
        else:
            info["Ошибка"] = "Неподдерживаемый формат аудиофайла."
            return info

        if audio:
            # Извлечение длительности
            if audio.info and hasattr(audio.info, 'length'):
                info["Длительность (сек)"] = int(audio.info.length)

            # Извлечение тегов в зависимости от типа файла
            if file_extension == '.mp3':
                # MP3 (ID3 tags)
                if 'TPE1' in audio.tags: # Artist
                    info["Исполнитель"] = str(audio.tags['TPE1'])
                if 'TIT2' in audio.tags: # Title
                    info["Название"] = str(audio.tags['TIT2'])
                if 'TALB' in audio.tags: # Album
                    info["Альбом"] = str(audio.tags['TALB'])
                if 'TCON' in audio.tags: # Genre
                    info["Жанр"] = str(audio.tags['TCON'])
                if 'TDRC' in audio.tags: # Year (for ID3v2.4)
                    info["Год"] = str(audio.tags['TDRC'])
                elif 'TYER' in audio.tags: # Year (for ID3v2.3)
                    info["Год"] = str(audio.tags['TYER'])
            elif file_extension in ['.flac', '.ogg', '.oga']:
                # FLAC and Ogg Vorbis use similar tag structures
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
            elif file_extension in ['.m4a', '.mp4']:
                # M4A/MP4 (iTunes style tags)
                if '\xa9ART' in audio.tags: # Artist
                    info["Исполнитель"] = audio.tags['\xa9ART'][0]
                if '\xa9nam' in audio.tags: # Title
                    info["Название"] = audio.tags['\xa9nam'][0]
                if '\xa9alb' in audio.tags: # Album
                    info["Альбом"] = audio.tags['\xa9alb'][0]
                if '\xa9gen' in audio.tags: # Genre
                    info["Жанр"] = audio.tags['\xa9gen'][0]
                if '\xa9day' in audio.tags: # Year
                    info["Год"] = audio.tags['\xa9day'][0]
            elif file_extension == '.wma':
                # WMA (ASF tags)
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

def rename(audio_files_info,output_dir):
    for info in audio_files_info:
        artist=info.get("Исполнитель")
        name=info.get("Название")
        direct=info.get("Директория")
        path=info.get("Путь к файлу")
        ext=info.get("Тип файла")
        #Очистка от недопустимых символов
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            artist = artist.replace(char, '_')
            name = name.replace(char, '_')
        artist = artist.replace(' ', '_')
        name = name.replace(' ', '_')
    if name != "Неизвестно" or artist != "Неизвестно":
        source=path
        dest=(f"{direct}/{name}-{artist}{ext}")
        if dest != source:
            print(f"\nИнициированано переимнование {path}")
            os.rename(source,dest)
        else:
            print(f"{dest} уже переименован. Пропущено.")
    else:
        print("Неизвестно название или исполнитель. Переименование не выполнено")
    for info in audio_files_info:
        info["Путь к файлу"] = dest
def organize_by_artist(audio_files_info, base_output_directory):
    """
    Создает папки для исполнителей и перемещает в них соответствующие треки.
    """
    print(f"\n--- Организация треков по исполнителям в директории: {base_output_directory} ---")

    # Создаем базовую выходную директорию, если она не существует
    os.makedirs(base_output_directory, exist_ok=True)

    moved_count = 0
    for info in audio_files_info:
        artist = info.get("Исполнитель")
        original_path = info.get("Путь к файлу")
        file_name = info.get("Название файла")

        if artist and artist != "Неизвестно" and original_path and os.path.exists(original_path):
            # Используем первый найденный исполнитель для имени папки
            main_artist = artist.split(',')[0].strip()
            
            # Очищаем имя папки от недопустимых символов
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                main_artist = main_artist.replace(char, '_')
            main_artist = main_artist.replace(' ', '_')

            artist_folder_path = os.path.join(base_output_directory, main_artist)
            
            # Создаем папку для исполнителя
            os.makedirs(artist_folder_path, exist_ok=True)

            destination_path = os.path.join(artist_folder_path, file_name)

            try:
                # Проверяем, не находится ли файл уже в целевой директории
                if os.path.abspath(original_path) == os.path.abspath(destination_path):
                    print(f"Файл '{file_name}' уже находится в целевой директории '{artist_folder_path}'. Пропущено.")
                    continue
                
                shutil.move(original_path, destination_path)
                print(f"Перемещено: '{file_name}' из '{os.path.dirname(original_path)}' в '{artist_folder_path}'")
                moved_count += 1
            except shutil.Error as e:
                print(f"Ошибка при перемещении файла '{file_name}': {e}")
            except Exception as e:
                print(f"Неизвестная ошибка при перемещении файла '{file_name}': {e}")
        elif not (artist and artist != "Неизвестно"):
            print(f"Пропущено '{file_name}': Неизвестный исполнитель.")
        else:
            print(f"Пропущено '{file_name}': Файл не найден или путь некорректен: {original_path}")

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
    # Если --output-dir не указан, используем input-dir в качестве базовой директории для создания папок исполнителей
    base_output_directory = args.output_dir if args.output_dir else scan_directory

    if not os.path.isdir(scan_directory):
        print(f"Ошибка: Директория для сканирования '{scan_directory}' не найдена или не является директорией.")
        return

    print(f"Сканирование директории: {scan_directory} и всех поддиректорий...\n")

    audio_extensions = ('.mp3', '.flac', '.ogg', '.oga', '.m4a', '.mp4', '.wma')
    all_audio_info = []
    found_audio_files = False
    for root, dirs, files in os.walk(scan_directory):
        for item in files:
            file_path = os.path.join(root, item)
            if item.lower().endswith(audio_extensions):
                found_audio_files = True
                info = get_audio_info(file_path)
                all_audio_info.append(info)
                # Выводим информацию о каждом файле только если не выполняем сортировку
                if not args.sort and not args.rename:
                    print(f"--- Информация о файле: {file_path} ---")
                    for key, value in info.items():
                        print(f"  {key}: {value}")
                    print("-" * 30)


    if not found_audio_files:
        print("Аудиофайлы не найдены в указанной директории или ее поддиректориях.")
        print("Убедитесь, что в этой директории или ее поддиректориях есть файлы с расширениями:")
        print(f"{', '.join(audio_extensions)}")
        print("Или поместите несколько аудиофайлов для тестирования.")
    else:
        # Выполняем сортировку, если флаг --sort установлен
        if args.sort:
            print(f"\nИнициирована сортировка треков по исполнителям.")
            organize_by_artist(all_audio_info, base_output_directory)
        # Переименование, если флаг --rename установлен
        for root, dirs, files in os.walk(base_output_directory):
            for item in files:
                file_path = os.path.join(root, item)
                if item.lower().endswith(audio_extensions):
                    found_audio_files = True
                    info = get_audio_info(file_path)
                    all_audio_info.append(info)
                    if args.rename:
                        rename(all_audio_info,base_output_directory)
           
        # Всегда выводим список всех исполнителей
        artists_list = get_unique_artists(all_audio_info)
        list_all_artists(artists_list)

if __name__ == "__main__":
    main()
#ну сами уже поняли что нейронки юзал
#тг автора @FRST4
