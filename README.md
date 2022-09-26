# Universal Auto
This repo is supposed to get statistics from Uber, Bold, Uklon to calculate performance of car cross this aggregators for fleet owners and provide reports via telegram bit for Drivers, Fleet Managers and Fleet Owners. 

# How to run a project on your local machine?
1. Install Docker https://docs.docker.com/engine/install/
2. Create a telegram bot using https://t.me/BotFather and get TELEGRAM_TOKEN 
3. Rename docker-compose_example.yml to docker-compose.yml
4. Replace <add your telegram token here> with token given by telegram 
5. Run `docker-compose up --build`
6. Run migrations by `docker exec -it universal_auto_web_1 python manage.py migrate`
7. Open http://localhost:8080/ in browser

# How to run report and see results in console?
```
docker exec -it universal_auto_web_1 python manage.py runscript weekly
```

# How to start contribute?

1. Take an issue from the list  https://github.com/SergeyKutsko/universal_auto/issues and ask questions
2. Fork project and create a new branch from a master branch with the name in the format: issues-12-your_last_name
3. After work is finished and covered by tests create a Pull Request with good description what exactly you did and how and add Sergey Kutsko as reviewer. 
4. After review fix found problems
5. Manual QA stage need to be done by other person to confirm solutions works as expected
6. We will deploy to staging server to confirm it works in pre-pod ENV
7. Merge into master and deploy to production instance. 
