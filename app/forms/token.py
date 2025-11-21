from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class TokenForm(FlaskForm):
    """Форма добавления/редактирования токена маркетплейса"""
    name = StringField('Название токена', 
                      validators=[
                          Optional(),
                          Length(max=100, message='Название не должно превышать 100 символов')
                      ],
                      render_kw={'placeholder': 'Например: Основной магазин, Тестовый аккаунт'})
    marketplace = SelectField('Маркетплейс', 
                             choices=[
                                 ('wildberries', 'Wildberries'),
                                 ('ozon', 'Ozon'),
                                 ('telegram', 'Telegram')
                             ],
                             validators=[DataRequired(message='Выберите маркетплейс')])
    token = TextAreaField('API Token', 
                         validators=[
                             DataRequired(message='Введите токен'),
                             Length(min=10, max=500, message='Токен должен быть от 10 до 500 символов')
                         ],
                         render_kw={'rows': 3, 'placeholder': 'Вставьте ваш API токен'})
    client_id = StringField('Client ID (только для Ozon)', 
                           validators=[Optional(), Length(max=200)],
                           render_kw={'placeholder': 'Введите Client ID для Ozon'})
    submit = SubmitField('Сохранить токен')

