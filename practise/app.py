from flask import Flask 
from extensions import bcrypt
from routes.auth import auth_bp
from routes.lawyer import cases_bp
from routes.admin import admin_bp
from routes.client import client_bp
from routes.document import document_bp
from routes.hearing import hearing_bp
from routes.notification import notification_bp
from routes.judgement import judgement_bp
from routes.report import report_bp
from routes.staff import staff_bp
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

bcrypt.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(cases_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(client_bp)
app.register_blueprint(document_bp)
app.register_blueprint(hearing_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(judgement_bp)
app.register_blueprint(report_bp)
app.register_blueprint(staff_bp)

if __name__ == "__main__":
    # app.run(host="0.0.0.0",port=5000,debug=True)     # for mobile(http://192.168.43.207:5000)
    app.run(debug=True)

