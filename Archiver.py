import os
import sys

'''ARCHIVE FORMAT:
1.filename/directory name
2.ZERO BYTE
3.ISFILE (0x00 if object is directory, 0xFF otherwise)
3.filesize, 12 byte field (if directory is encoded, this field can be filled with anything)
4.file content itself
5.ZERO BYTE'''

CHUNK_SIZE = 32768
END_OF_BLOCK = 0x00.to_bytes(1)

class Archiver:

    def create_archive(self, path_to):
        archive_path = path_to + '.archive'
        file = open(archive_path, 'wb')
        if os.path.isfile(path_to):
            self._write_archived_file(path_to)
            return
        folders = [self._get_name(path_to)]
        for cur_dir, subfolders, files in os.walk(path_to):
            cur_folder = self._get_name(cur_dir)
            while folders[-1] != cur_folder:
                folders.pop()
                file.write(END_OF_BLOCK)
            folders.extend(reversed(subfolders))
            file.write(self._get_header(self._get_name(cur_dir), False))

            for filename in files:
                self._write_archived_file('\\'.join((cur_dir, filename)), file)
        while folders:
            folders.pop()
            file.write(END_OF_BLOCK)
        file.close()
        return archive_path
    
    def _get_name(self, path):
        return path.rsplit('\\',1)[-1]
        
    def _get_header(self, name, is_file, filesize=0):
        header = bytearray()
        header.extend(str.encode(name, encoding='ascii'))
        header.extend(END_OF_BLOCK)
        header.append(0xFF if is_file else 0x00)
        header.extend(filesize.to_bytes(12))
        return header
    
    def _write_archived_file(self, path_to, file):
        filesize = os.path.getsize(path_to)
        file.write(self._get_header(self._get_name(path_to), True, filesize))
        with open(path_to, 'rb') as reader:
            while data := reader.read(CHUNK_SIZE):
                file.write(data)
        file.write(END_OF_BLOCK)
    
class Dearchiver:
    def __init__(self):
        self._buffer = bytearray()

    def unarchive(self, path_to):
        reader = open(path_to, 'rb')
        directory = os.getcwd()
        while True:
            name, isfile = self._try_write_file(directory, reader)
            if not isfile:
                directory += f'\\{name}'
            while True:
                byte = reader.peek(1)[:1]
                if byte == b'':
                    reader.close()
                    return
                if byte == END_OF_BLOCK:
                    reader.read(1)
                    directory = directory.rsplit('\\',1)[0]
                else:
                    break
    
    def _read_until_end_of_block(self, reader):
        data = bytearray()
        while (byte := reader.read(1)) != END_OF_BLOCK:   
            data.extend(byte)
        return data

    def _write_file(self, path, length, reader):
        with open(path, 'wb') as f:
            while length:
                data = reader.read(min(length, CHUNK_SIZE))
                f.write(data)
                length -= len(data)

    def _try_write_file(self, directory, reader):
        name_bytes = self._read_until_end_of_block(reader)
        name = name_bytes.decode(encoding='ascii')
        is_file = reader.read(1)[0] == 0xFF
        filesize = int.from_bytes(reader.read(12))
        path_to = '\\'.join((directory, name))
        if is_file:
            self._write_file(path_to, filesize, reader)
        else:
            if os.path.exists(path_to):
                path_to += '-1'
                name += '-1'
            os.mkdir(path_to)
        if is_file:
            reader.read(1)
        return name, is_file