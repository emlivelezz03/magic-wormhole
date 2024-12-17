from setuptools import setup
import versioneer

# Получаем команды для версии с помощью versioneer
commands = versioneer.get_cmdclass()

# Классификаторы для описания пакета
trove_classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Security :: Cryptography",
    "Topic :: System :: Networking",
    "Topic :: System :: Systems Administration",
    "Topic :: Utilities",
]

# Описание и установка пакета
setup(
    name="magic-wormhole",  # Название пакета
    version=versioneer.get_version(),  # Получаем версию через versioneer
    description="Securely transfer data between computers",  # Краткое описание
    long_description=open('README.md', 'r').read(),  # Длинное описание из файла README.md
    long_description_content_type='text/markdown',  # Формат длинного описания
    author="Brian Warner",  # Автор
    author_email="warner-magic-wormhole@lothar.com",  # Электронная почта автора
    license="MIT",  # Лицензия
    url="https://github.com/warner/magic-wormhole",  # Ссылка на репозиторий
    classifiers=trove_classifiers,  # Классификаторы для пакета

    # Указываем местоположение исходного кода пакета
    package_dir={"": "src"},
    packages=[
        "wormhole",
        "wormhole.cli",
        "wormhole._dilation",
        "wormhole.test",
        "wormhole.test.dilate",
    ],

    # Указываем дополнительные файлы, которые нужно установить
    data_files=[(".", ["wormhole_complete.bash", "wormhole_complete.zsh", "wormhole_complete.fish"])],

    # Входные точки для консольных скриптов
    entry_points={
        "console_scripts": [
            "wormhole = wormhole.cli.cli:wormhole",  # Определяем команду `wormhole` для CLI
        ]
    },

    # Зависимости, которые необходимы для работы пакета
    install_requires=[
        "spake2==0.9", "pynacl",
        "attrs >= 19.2.0",  # 19.2.0 заменяет параметр cmp на eq/order
        "twisted[tls] >= 17.5.0",  # 17.5.0 добавляет failAfterFailures
        "autobahn[twisted] >= 0.14.1",
        "automat",
        "cryptography",
        "tqdm >= 4.13.0",  # 4.13.0 исправляет сбой на NetBSD
        "click",
        "humanize",
        "txtorcon >= 18.0.2",  # 18.0.2 исправляет поддержку py3.4
        "zipstream-ng >= 1.7.1, <2.0.0",
        "iterable-io >= 1.0.0, <2.0.0",
        "qrcode >= 8.0",
    ],

    # Дополнительные зависимости для различных окружений
    extras_require={
        ':sys_platform=="win32"': ["pywin32"],  # Для Windows
        "dev": ["tox", "pyflakes",  # Для разработки
                "magic-wormhole-transit-relay==0.3.1",
                "magic-wormhole-mailbox-server==0.3.1"],
        "dilate": ["noiseprotocol"],  # Для расширенной функциональности
        "build": ["twine", "dulwich", "readme_renderer", "gpg", "wheel"],  # Для сборки
    },

    # Указываем тестовую директорию
    test_suite="wormhole.test",  # Тесты, которые будут выполняться

    # Устанавливаем команды для работы с версиями
    cmdclass=commands,
)

