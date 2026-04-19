from plyer import notification


class Notifier:
    def notify(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Focus Mode",
                timeout=10,
            )
        except Exception:
            pass
