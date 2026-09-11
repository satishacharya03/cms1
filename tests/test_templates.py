import jinja2
import pytest

def test_templates_rendering():
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('app/templates'),
        autoescape=True
    )

    # 1. Test base.html
    t_base = env.get_template('base.html')
    out_base_logged_in = t_base.render(user={'email': 'prof@chandigarh.edu', 'role': 'data_manager'})
    assert 'MATRIXCMS' in out_base_logged_in
    assert 'Chandigarh CSE Expedition &amp; Research Portal' in out_base_logged_in or 'Chandigarh CSE' in out_base_logged_in
    assert 'Home' in out_base_logged_in
    assert 'Expeditions' in out_base_logged_in
    assert 'Data Catalog' in out_base_logged_in
    assert 'Reports' in out_base_logged_in
    assert 'Publications' in out_base_logged_in
    assert 'Media' in out_base_logged_in
    assert 'News &amp; Activities' in out_base_logged_in or 'News & Activities' in out_base_logged_in
    assert 'About' in out_base_logged_in
    assert 'prof@chandigarh.edu' in out_base_logged_in
    assert 'DATA MANAGER' in out_base_logged_in
    assert 'Admin' in out_base_logged_in
    assert 'Logout' in out_base_logged_in
    assert '/static/css/style.css' in out_base_logged_in
    assert 'Chandigarh' in out_base_logged_in
    assert 'CSE' in out_base_logged_in
    assert 'CC-BY-4.0' in out_base_logged_in

    out_base_anon = t_base.render()
    assert 'Login' in out_base_anon
    assert 'Register' in out_base_anon

    # 2. Test home.html
    t_home = env.get_template('home.html')
    out_home = t_home.render(
        metrics={'active_expeditions': 7, 'open_datasets': 44, 'published_reports': 52, 'peer_reviewed_papers': 23},
        search_query=''
    )
    assert '/search' in out_home
    assert 'Active Expeditions' in out_home
    assert 'Open Datasets' in out_home
    assert 'Published Reports' in out_home
    assert 'Peer-Reviewed Papers' in out_home
    assert 'Featured &amp; Recent Expeditions' in out_home or 'Featured & Recent Expeditions' in out_home
    assert 'Latest Scientific Datasets' in out_home
    assert 'Recent Activities &amp; Outreach Summaries' in out_home or 'Recent Activities & Outreach Summaries' in out_home

    # 3. Test about.html
    t_about = env.get_template('about.html')
    out_about = t_about.render()
    assert 'Chandigarh' in out_about
    assert 'Computer Science &amp; Engineering' in out_about or 'Computer Science & Engineering' in out_about
    assert 'Open Science' in out_about
    assert 'Expedition Archival' in out_about
    assert 'Groq' in out_about
    assert 'Cloudflare Workers AI' in out_about
    assert 'Llama 3.1' in out_about or 'Llama' in out_about
    assert 'CC-BY-4.0' in out_about
    assert 'DOI' in out_about
    assert 'FAIR' in out_about
    assert 'cse-expeditions@chandigarh.edu' in out_about

    # 4. Test login.html
    t_login = env.get_template('login.html')
    out_login = t_login.render()
    assert 'admin@chandigarh.edu' in out_login
    assert 'admin123' in out_login
    assert 'name="email"' in out_login
    assert 'name="password"' in out_login
    assert '/register' in out_login

    # 5. Test register.html
    t_register = env.get_template('register.html')
    out_register = t_register.render()
    assert 'name="email"' in out_register
    assert 'name="password"' in out_register
    assert 'name="role"' in out_register
    assert '/login' in out_register

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_templates_rendering()
