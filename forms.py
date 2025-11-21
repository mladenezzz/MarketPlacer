from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from models import User

class RegistrationForm(FlaskForm):
    """Форма регистрации"""
    username = StringField('Имя пользователя', 
                          validators=[
                              DataRequired(message='Это поле обязательно'),
                              Length(min=3, max=80, message='Имя должно быть от 3 до 80 символов')
                          ])
    email = StringField('Email', 
                       validators=[
                           DataRequired(message='Это поле обязательно'),
                           Email(message='Введите корректный email адрес')
                       ])
    password = PasswordField('Пароль', 
                            validators=[
                                DataRequired(message='Это поле обязательно'),
                                Length(min=6, message='Пароль должен быть минимум 6 символов')
                            ])
    password2 = PasswordField('Подтвердите пароль', 
                             validators=[
                                 DataRequired(message='Это поле обязательно'),
                                 EqualTo('password', message='Пароли должны совпадать')
                             ])
    submit = SubmitField('Зарегистрироваться')
    
    def validate_username(self, username):
        """Проверка уникальности имени пользователя"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Выберите другое.')
    
    def validate_email(self, email):
        """Проверка уникальности email"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован. Используйте другой.')

class LoginForm(FlaskForm):
    """Форма входа"""
    username = StringField('Имя пользователя или Email', 
                          validators=[DataRequired(message='Это поле обязательно')])
    password = PasswordField('Пароль', 
                            validators=[DataRequired(message='Это поле обязательно')])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

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


class TokenForm(FlaskForm):
    """Форма добавления/редактирования токена маркетплейса"""
    marketplace = SelectField('Маркетплейс', 
                             choices=[
                                 ('wildberries', 'Wildberries'),
                                 ('ozon', 'Ozon')
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

