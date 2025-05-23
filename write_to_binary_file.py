import random
import string
import sqlite3
from pathlib import Path

characters = string.ascii_letters + string.digits
ID_LENGTH = 11
def random_video(length: int) -> tuple[str, int]:
    s = ''.join(random.choice(characters) for _ in range(ID_LENGTH))
    return s, random.randint(1, 10_000_000)


def generate_random_data(n: int) -> list[tuple[str, int]]:
    return [random_video(11) for _ in range(n)]


def write_to_sqlite(db_name: str, data: list[tuple[str, int]]) -> None:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS videos (
        id CHAR({ID_LENGTH}) PRIMARY KEY,
        views INTEGER
    );
    """)
    conn.commit()
    for video_id, views in data:
        cursor.execute(f"INSERT INTO videos (id, views) VALUES ('{video_id}', {views});")
    conn.commit()
    conn.close()


def truncate_views(views: int) -> tuple[str, int]:
    v = str(views)
    if len(v) <= 2:
        return v.ljust(3, '0'), 0
    right_pad = len(v) - 3
    return v[:3], right_pad


def restore_views(sig_digits: int | str, num_zeros: int) -> int:
    return int(sig_digits) * (10 ** num_zeros)


VERSION_NUMBER = 0

def write_to_binary_file(file_path: Path,
                         video_id_length: int,
                         data: list[tuple[str, int]],
                         relax_video_id_length: bool = False) -> None:
    file = open(file_path, 'wb')
    result = bytearray()

    # version marker
    result.append(VERSION_NUMBER)

    result.append(video_id_length)

    # 2 reserved bytes
    result.extend((0, 0))

    # store number of entries as 4-byte integer (big endian)
    n = len(data)
    result.extend(n.to_bytes(4, byteorder='big'))

    # write each entry
    for video_id, views in data:
        if relax_video_id_length:
            assert len(video_id) <= video_id_length
            video_id = video_id.rjust(video_id_length, ' ')
        else:
            assert len(video_id) == video_id_length

        vid_bytes = video_id.encode('ascii')
        result.extend(vid_bytes)

        sig_digits, num_zeros = truncate_views(views)

        # Combine into 16-bit value: first 10 bits = sig_digits, last 6 bits = zeros
        encoded = (int(sig_digits) << 6) | num_zeros
        result.extend(encoded.to_bytes(2, byteorder='big'))

    file.write(result)
    file.close()

def read_binary_file(binary_file: Path) -> list[tuple[str, int]]:
    file = open(binary_file, 'rb')

    byte_array = bytearray(file.read())

    assert byte_array[0] == VERSION_NUMBER
    video_id_length = int(byte_array[1])

    n = int.from_bytes(byte_array[4:8], byteorder='big')

    result: list[tuple[str, int]] = []

    start_byte = 8
    step = video_id_length + 2
    end_byte = start_byte + n * step
    for current_byte in range(start_byte, end_byte, step):
        mid_byte = current_byte + video_id_length
        video_id = byte_array[current_byte:mid_byte].decode('ascii')
        raw_views = int.from_bytes(byte_array[mid_byte:mid_byte + 2], byteorder='big')
        sig_digits = raw_views >> 6
        num_zeros = raw_views & 0b111111
        result.append((video_id, restore_views(sig_digits, num_zeros)))
    return result

def verify_binary_file(binary_file: Path, data: list[tuple[str, int]]) -> bool:
    result = read_binary_file(binary_file)
    assert len(result) == len(data)
    for i in range(len(result)):
        expected = data[i]
        actual = result[i]
        assert expected[0] == actual[0]
        views_expected = restore_views(*truncate_views(expected[1]))
        views_actual = actual[1]
        assert views_expected == views_actual
    print("Binary file verified")


def test_write():
    data = generate_random_data(100000)

    db_file = Path("test.db")
    write_to_sqlite(str(db_file), data)
    db_file.unlink()

    binary_file = Path('test.bin')
    write_to_binary_file(binary_file, ID_LENGTH, data)
    verify_binary_file(binary_file, data)
    binary_file.unlink()

binary_file_root = Path("view_counts")
binary_file_root.mkdir(parents=True, exist_ok=True)

def write_yt_file():
    file_dir = binary_file_root / "yt.bin"
    write_to_binary_file(file_dir, 11, [('L0tcMxp8Iy8', 2_345_678)])


def write_nn_file():
    file_dir = binary_file_root / "nn.bin"
    write_to_binary_file(file_dir, 12, [('sm22001720', 9_999_999)], relax_video_id_length=True)


def main():
    write_yt_file()
    write_nn_file()


if __name__ == '__main__':
    main()