from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class ChangeRoleForm(FlaskForm):
    """Форма изменения роли пользователя"""
    role = SelectField('Роль', 
                      choices=[
                          ('user', 'Пользователь'),
                          ('admin', 'Администратор'),
                          ('analyst', 'Аналитик'),
                          ('accountant', 'Бухгалтер')
                      ],
                      validators=[DataRequired(message='Выберите роль')])
    submit = SubmitField('Изменить роль')

