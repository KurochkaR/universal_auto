import pytest
from app.models import Report_of_driver_debt

@pytest.mark.django_db
@pytest.mark.parametrize('driver,image', [('Олександр Холін','photo_2023-02-28_12-05-09.jpg'),
                                          ('Анатолій Мухін', 'photo_2023-02-28_12-05-09'),
                                          ('Сергій Желамський', 'photo.png'),
                                          ('Олег Філіппов', 'Юрій Філіппов'),
                                    ])
def test_report_debt_model(driver, image):
    report = Report_of_driver_debt.objects.create(driver=driver, image=image)
    assert report.driver == driver
    assert report.image == image
    assert report.admin_image == f'<img src="{image.url}" width="200" />'
    assert Report_of_driver_debt.objects.count() == 1
