from db import get_conn

with get_conn() as conn:
    rows = conn.execute("""
        SELECT u.login, u.password, r.name as role
        FROM user u
        JOIN role r ON r.id = u.role_id
        ORDER BY u.id
    """).fetchall()

print("USERS IN DB:")
for r in rows:
    print(r["login"], r["password"], "-", r["role"])
