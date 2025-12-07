from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError


class ChangeRoleForm(FlaskForm):
    """Форма изменения роли пользователя"""
    role = SelectField('Роль',
                      choices=[
                          ('admin', 'Администратор'),
                          ('manager', 'Менеджер'),
                          ('warehouse', 'Склад'),
                      ],
                      validators=[DataRequired(message='Выберите роль')])
    submit = SubmitField('Изменить роль')


class CreateUserForm(FlaskForm):
    """Форма создания пользователя администратором"""
    username = StringField('Имя пользователя',
                          validators=[
                              DataRequired(message='Введите имя пользователя'),
                              Length(min=3, max=80, message='Имя должно быть от 3 до 80 символов')
                          ])
    password = PasswordField('Пароль',
                            validators=[
                                DataRequired(message='Введите пароль'),
                                Length(min=6, message='Пароль должен быть не менее 6 символов')
                            ])
    password_confirm = PasswordField('Подтверждение пароля',
                                    validators=[
                                        DataRequired(message='Подтвердите пароль'),
                                        EqualTo('password', message='Пароли не совпадают')
                                    ])
    role = SelectField('Роль',
                      choices=[
                          ('manager', 'Менеджер'),
                          ('warehouse', 'Склад'),
                          ('admin', 'Администратор'),
                      ],
                      validators=[DataRequired(message='Выберите роль')])
    submit = SubmitField('Создать пользователя')

    def validate_username(self, field):
        from app.models import User
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Пользователь с таким именем уже существует')

