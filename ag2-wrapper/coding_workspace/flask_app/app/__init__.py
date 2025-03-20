from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=None):
    """创建并配置Flask应用"""
    app = Flask(__name__, 
                instance_relative_config=True,
                template_folder='../templates', 
                static_folder='../static')
    
    # 加载配置
    if config_class is None:
        app.config.from_object('config.DevelopmentConfig')
    else:
        app.config.from_object(config_class)
    
    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # 蓝图注册
    from app.views import main_bp
    app.register_blueprint(main_bp)
    
    return app
