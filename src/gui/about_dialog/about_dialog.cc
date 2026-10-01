// Copyright 2010-2021, Google Inc.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
//     * Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
//     * Neither the name of Google Inc. nor the names of its
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include "gui/about_dialog/about_dialog.h"

#include <QtGui>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QTemporaryFile>
#include <algorithm>
#include <memory>
#include <string>

#include "base/file_util.h"
#include "base/process.h"
#include "base/run_level.h"
#include "base/system_util.h"
#include "base/version.h"
#include "gui/base/util.h"

namespace mozc {
namespace gui {
namespace {

void defaultLinkActivated(const QString &str) {
  QByteArray utf8 = str.toUtf8();
  Process::OpenBrowser(std::string(utf8.data(), utf8.length()));
}

inline void Replace(QString &str, const char pattern[], const char repl[]) {
  str.replace(QLatin1String(pattern), QLatin1String(repl));
}

inline void Replace(QString &str, const char pattern[], const QString &repl) {
  str.replace(QLatin1String(pattern), repl);
}

QString ReplaceString(const QString &str) {
  QString replaced(str);
  Replace(replaced, "[ProductName]", GuiUtil::ProductName());

  Replace(replaced, "[ProductUrl]",
          "https://github.com/hglasswater-boop/mozc-date");
  Replace(replaced, "[ForumUrl]", "https://github.com/hglasswater-boop/mozc-date/issues");
  Replace(replaced, "[ForumName]", QObject::tr("issues"));

  const std::string credit_filepath =
      FileUtil::JoinPath(SystemUtil::GetDocumentDirectory(), "credits_en.html");
  Replace(replaced, "credits_en.html", credit_filepath.c_str());

  return replaced;
}

void SetLabelText(QLabel *label) {
  label->setText(ReplaceString(label->text()));
}

#ifdef _WIN32
QString ExtractUpdaterScript() {
  QFile resource(QStringLiteral(":/update-mozc-minimal.ps1"));
  if (!resource.open(QIODevice::ReadOnly)) {
    return {};
  }
  QTemporaryFile script(QDir::tempPath() +
                        QStringLiteral("/mozc-date-updater-XXXXXX.ps1"));
  if (!script.open()) {
    return {};
  }
  const QByteArray content = resource.readAll();
  if (script.write(content) != content.size()) {
    return {};
  }
  script.setAutoRemove(false);
  const QString path = script.fileName();
  script.close();
  return path;
}
#endif  // _WIN32
}  // namespace

AboutDialog::AboutDialog(QWidget *parent)
    : QDialog(parent), callback_(nullptr) {
  setupUi(this);
  setWindowFlags(Qt::WindowSystemMenuHint | Qt::WindowCloseButtonHint);
  setWindowModality(Qt::NonModal);
  QPalette window_palette;
  window_palette.setColor(QPalette::Window, QColor(255, 255, 255));
  window_palette.setColor(QPalette::WindowText, QColor(0, 0, 0));
  setPalette(window_palette);
  setAutoFillBackground(true);
  std::string version_info = "(" + Version::GetMozcVersion() + ")";
  version_label->setText(QLatin1String(version_info.c_str()));
  GuiUtil::ReplaceWidgetLabels(this);

  QPalette palette;
  palette.setColor(QPalette::Window, QColor(236, 233, 216));
  color_frame->setPalette(palette);
  color_frame->setAutoFillBackground(true);

  // change font size for product name
  QFont font = label->font();
#ifdef _WIN32
  font.setPointSize(22);
#endif  // _WIN32

#ifdef __APPLE__
  font.setPointSize(26);
#endif  // __APPLE__

  label->setFont(font);

  SetLabelText(label_terms);
  SetLabelText(label_credits);

#ifdef _WIN32
  const QString current_version =
      QString::fromStdString(Version::GetMozcVersion()).trimmed();
  updateButton->setEnabled(false);
  updateStatusLabel->setText(
      QString::fromUtf8("現在のバージョン: %1").arg(current_version));

  QObject::connect(checkUpdateButton, &QPushButton::clicked, this,
                   [this, current_version]() {
    const QString script_path = ExtractUpdaterScript();
    if (script_path.isEmpty()) {
      updateStatusLabel->setText(
          QString::fromUtf8("更新ツールを読み込めませんでした。"));
      return;
    }
    checkUpdateButton->setEnabled(false);
    updateButton->setEnabled(false);
    updateStatusLabel->setText(QString::fromUtf8("更新を確認しています..."));

    auto *process = new QProcess(this);
    QObject::connect(process,
                     static_cast<void (QProcess::*)(int, QProcess::ExitStatus)>(
                         &QProcess::finished),
                     this,
                     [this, process, script_path, current_version](
                         int exit_code, QProcess::ExitStatus exit_status) {
      checkUpdateButton->setEnabled(true);
      QFile::remove(script_path);
      if (exit_status != QProcess::NormalExit || exit_code != 0) {
        updateStatusLabel->setText(
            QString::fromUtf8("更新確認に失敗しました。"));
        updateStatusLabel->setToolTip(
            QString::fromUtf8(process->readAllStandardError()).trimmed());
      } else {
        const QString latest =
            QString::fromUtf8(process->readAllStandardOutput()).trimmed();
        if (latest.isEmpty()) {
          updateStatusLabel->setText(
              QString::fromUtf8("最新バージョンを取得できませんでした。"));
        } else if (Version::CompareVersion(current_version.toStdString(),
                                            latest.toStdString())) {
          updateStatusLabel->setText(
              QString::fromUtf8("更新があります: %1 → %2")
                  .arg(current_version, latest));
          updateButton->setEnabled(true);
        } else {
          updateStatusLabel->setText(
              QString::fromUtf8("最新版です（%1）").arg(current_version));
        }
      }
      process->deleteLater();
    });
    QObject::connect(process, &QProcess::errorOccurred, this,
                     [this, process, script_path](QProcess::ProcessError error) {
      if (error != QProcess::FailedToStart) {
        return;
      }
      QFile::remove(script_path);
      checkUpdateButton->setEnabled(true);
      updateStatusLabel->setText(
          QString::fromUtf8("更新ツールを起動できませんでした。"));
      updateStatusLabel->setToolTip(process->errorString());
      process->deleteLater();
    });
    process->start(QStringLiteral("powershell.exe"),
                   {QStringLiteral("-NoProfile"),
                    QStringLiteral("-NonInteractive"),
                    QStringLiteral("-ExecutionPolicy"),
                    QStringLiteral("Bypass"), QStringLiteral("-File"),
                    script_path, QStringLiteral("-Check")});
  });

  QObject::connect(updateButton, &QPushButton::clicked, this,
                   [this, current_version]() {
    const QString script_path = ExtractUpdaterScript();
    if (script_path.isEmpty() ||
        !QProcess::startDetached(
            QStringLiteral("powershell.exe"),
            {QStringLiteral("-NoProfile"),
             QStringLiteral("-ExecutionPolicy"),
             QStringLiteral("Bypass"), QStringLiteral("-File"), script_path,
             QStringLiteral("-CurrentVersion"), current_version})) {
      updateStatusLabel->setText(
          QString::fromUtf8("更新ツールを起動できませんでした。"));
      return;
    }
    checkUpdateButton->setEnabled(false);
    updateButton->setEnabled(false);
    updateStatusLabel->setText(
        QString::fromUtf8("更新ツールを起動しました。画面の案内に従ってください。"));
  });
#else
  updateWidget->hide();
#endif  // _WIN32

  product_image_ =
      std::make_unique<QImage>(QLatin1String(":/product_logo.png"));
}

void AboutDialog::paintEvent(QPaintEvent *event) {
  // draw product logo
  QPainter painter(this);
  const QRect image_rect = product_image_->rect();
  // allow clipping on right / bottom borders
  const QRect draw_rect(std::max(5, width() - image_rect.width() - 15),
                        std::max(0, color_frame->y() - image_rect.height()),
                        image_rect.width(), image_rect.height());
  painter.drawImage(draw_rect, *product_image_);
}

void AboutDialog::SetLinkCallback(LinkCallbackInterface *callback) {
  callback_ = callback;
}

void AboutDialog::linkActivated(const QString &link) {
  // we don't activate the link if about dialog is running as root
  if (!RunLevel::IsValidClientRunLevel()) {
    return;
  }
  if (callback_ != nullptr) {
    callback_->linkActivated(link);
  } else {
    defaultLinkActivated(link);
  }
}

}  // namespace gui
}  // namespace mozc
