// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later

#include <cstdio>
#include <QDir>
#include <QGuiApplication>
#include <QLibraryInfo>
#include <QTextStream>

int main(int argc, char** argv) {
    qInstallMessageHandler([](QtMsgType, const QMessageLogContext&, const QString& message) {
        const auto text = message.toUtf8();
        std::fwrite(text.constData(), 1, text.size(), stderr);
        std::fputc('\n', stderr);
        std::fflush(stderr);
    });
    std::fputs("Initializing packaged Qt platform...\n", stderr);
    std::fflush(stderr);
    QGuiApplication app{argc, argv};
    QTextStream output{stdout};
    const auto expected = QDir{QCoreApplication::applicationDirPath() + "/plugins"}.canonicalPath();
    const auto actual = QDir{QLibraryInfo::path(QLibraryInfo::PluginsPath)}.canonicalPath();
    output << "Qt platform: " << QGuiApplication::platformName() << '\n'
           << "Packaged plugin path: " << actual << '\n';
    if (QGuiApplication::platformName() != "windows" || expected.isEmpty() || actual != expected) {
        output << "The Windows platform must load using this package's Qt plugin directory.\n";
        return 1;
    }
    return 0;
}
