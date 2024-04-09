# Universal Auto
This repo is supposed to get statistics from Uber, Bolt, Uklon to calculate performance of car cross this aggregators for fleet owners and provide reports via telegram BOT for Drivers, Fleet Managers and Fleet Owners. 

# How to run a project on your local machine?
1. Install Docker https://docs.docker.com/engine/install/
2. Create a telegram bot using https://t.me/BotFather and get TELEGRAM_TOKEN 
3. Rename docker-compose_example.yml to docker-compose.yml
4. Replace <add your telegram token here> with token given by telegram
5. Run `docker-compose up --build pgadmin`
6. Open http://localhost:5050/browser/ with password: `universal_auto_dev` and create DB `universal_auto_dev`
7. Run `docker-compose up --build`
If you have error /data/db: permission denied failed to solve run: `sudo chmod -R 777 ./data/db`
8. Run migrations by `docker exec -it universal_auto_web python3 manage.py migrate`
9. Run to create admin user `docker exec -it universal_auto_web python3 manage.py createsuperuser` 
10. Open http://localhost/admin/ in browser and auth with user created at step 9
11. Run `docker exec -it universal_auto_web python3 manage.py runscript seed_db` to create test data
12. Run `docker exec -it universal_auto_web python3 manage.py runscript park_settings` to create park settings

# How to run report and see results in console?
```
docker exec -it universal_auto_web python3 manage.py runscript weekly
```

# How to start contribute?

1. Take an issue from the list  https://github.com/SergeyKutsko/universal_auto/issues and ask questions
2. Fork project and create a new branch from a master branch with the name in the format: issues-12-your_last_name
3. Ensure you run makemigrations by `docker exec -it universal_auto_web python3 manage.py makemigrations`
4. After work is finished and covered by tests create a Pull Request with good description what exactly you did and how and add Sergey Kutsko as reviewer. 
5. After review fix found problems
6. Manual QA stage need to be done by other person to confirm solutions works as expected
7. We will deploy to staging server to confirm it works in pre-prod ENV
8. Merge into master and deploy to production instance. 

# Documentation
1. Bot messages:
   - Статистика
        Відображає інформацію за поточний тиждень з понеділка 00:00 по неділю 23:59 за минулі дні поточного тижня, в дужках за вчора. 
        Якщо водій не працював то його в списку не буде або не буде інформації в дужках\
        Водій (прізвище та імʼя)\
        Автомобілі - список авто на яких працював даний водій\
        Каса - заробіток водія в агрегаторах Bolt Uklon Uber \
        Холостий пробіг - пробіг без замовлень без вирахування безкоштовних км\
        Ефективність - заробіток водія за кожний км який він проїхав\
        Виконано замовлень - кількість завершених замовлень\
        % прийнятих - відношення виконаних замовлень до усіх замовлень наданих агрегаторами у відсотках\
        Середній чек - відношення каси до виконаних замовлень \
        Пробіг - загальна кількість км що проїхав водій \
        Час в дорозі - час проведений в замовленнях \
