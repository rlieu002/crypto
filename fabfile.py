from fabric.api import *
from fabistrano import deploy
from fabric.api import env, sudo, run, put, task
from fabistrano.helpers import with_defaults


env.user = "build"
env.hosts = ["aw1"] # Replace with your host name or IP
env.base_dir = '/home/build' # Set to your app's directory
env.app_name = 'crypto' # This will deploy the app to /www/app_name.com/
env.git_clone = 'git@bitbucket.org:awaage66/crypto' # Your git url
env.remote_owner = "build"
env.remote_group = "build"

# env.restart_cmd = 'kill -HUP `supervisorctl pid gunicorn`' # Restart command
# or
# env.wsgi_path = "app_name/apache.wsgi" # Relative path to the wsgi file to be touched on restart

env.timeout = 6000

@task
@with_defaults
def restart():
    """Restarts your application"""
    try:
        run("touch %(current_release)s/%(wsgi_path)s" % \
                { 'current_release': env.current_release,
                  'wsgi_path': env.wsgi_path })
    except AttributeError:
        try:
            sudo(env.restart_cmd)
        except AttributeError:
            pass

@with_defaults
def permissions():
    """Make the release group-writable"""
    run("chown -R %(user)s:%(group)s %(domain_path)s" % 
            { 'domain_path':env.domain_path,
              'user': env.remote_owner,
              'group': env.remote_group })
    run("chmod -R g+w %(domain_path)s" % { 'domain_path':env.domain_path })

@task
@with_defaults
def setup():
    """Prepares one or more servers for deployment"""
    run("mkdir -p %(domain_path)s/{releases,shared}" % { 'domain_path':env.domain_path })
    run("mkdir -p %(shared_path)s/{system,log}" % { 'shared_path':env.shared_path })
    permissions()

@with_defaults
def checkout():
    """Checkout code to the remote servers"""
    from time import time
    env.current_release = "%(releases_path)s/%(time).0f" % { 'releases_path':env.releases_path, 'time':time() }
    run("cd %(releases_path)s; git clone -b %(git_branch)s -q %(git_clone)s %(current_release)s" % \
        { 'releases_path':env.releases_path,
          'git_clone':env.git_clone,
          'current_release':env.current_release,
          'git_branch':env.git_branch })

@task
def update():
    """Copies your project and updates environment and symlink"""
    update_code()
    update_env()
    symlink()
    set_current()
    permissions()

@task
def update_code():
    """Copies your project to the remote servers"""
    checkout()
    permissions()

@with_defaults
def symlink():
    """Updates the symlink to the most recently deployed version"""
    run("ln -nfs %(shared_path)s/log %(current_release)s/log" % { 'shared_path':env.shared_path, 'current_release':env.current_release })
    run("ln -nfs %(shared_path)s/.env %(current_release)s/.env" % { 'shared_path':env.shared_path, 'current_release':env.current_release })

@with_defaults
def set_current():
    """Sets the current directory to the new release"""
    run("ln -nfs %(current_release)s %(current_path)s" % { 'current_release':env.current_release, 'current_path':env.current_path })

@with_defaults
def update_env():
    """Update servers environment on the remote servers"""
    run("cd %(current_release)s; pipenv install" % { 'current_release':env.current_release })
    permissions()

@task 
@with_defaults
def cleanup():
    """Clean up old releases"""
    if len(env.releases) > 3:
        directories = env.releases
        directories.reverse()
        del directories[:3]
        env.directories = ' '.join([ "%(releases_path)s/%(release)s" % { 'releases_path':env.releases_path, 'release':release } for release in directories ])
        run("rm -rf %(directories)s" % { 'directories':env.directories })

@with_defaults
def rollback_code():
    """Rolls back to the previously deployed version"""
    if len(env.releases) >= 2:
        env.current_release = env.releases[-1]
        env.previous_revision = env.releases[-2]
        env.current_release = "%(releases_path)s/%(current_revision)s" % { 'releases_path':env.releases_path, 'current_revision':env.current_revision }
        env.previous_release = "%(releases_path)s/%(previous_revision)s" % { 'releases_path':env.releases_path, 'previous_revision':env.previous_revision }
        run("rm %(current_path)s; ln -s %(previous_release)s %(current_path)s && rm -rf %(current_release)s" % { 'current_release':env.current_release, 'previous_release':env.previous_release, 'current_path':env.current_path })

@task
def rollback():
    """Rolls back to a previous version and restarts"""
    rollback_code()
    restart()

@task(default=True)
def deploy():
    """Deploys your project. This calls both `update' and `restart'"""
    update()
    restart()
    restart_bot()
    restart_cron()

@task
@with_defaults
def restart_bot():
    """Start / stop bot"""
    run("sudo systemctl restart ckrypto_bot", pty=False)

@task
@with_defaults
def restart_cron():
    run("sudo systemctl restart ckrypto_cron", pty=False)