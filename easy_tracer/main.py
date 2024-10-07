import sys
from PyQt5.QtWidgets import QApplication
from views.main_view import MainView
from presenters.main_presenter import MainPresenter
from models.tracer_model import TracerModel


def main() -> None:
    """Main function to run the application."""
    app = QApplication(sys.argv)

    view = MainView()
    model = TracerModel()
    presenter = MainPresenter(view, model)

    view.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()