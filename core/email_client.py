
import os
import resend
from typing import List, Optional

class EmailClient:
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        if self.api_key:
            resend.api_key = self.api_key
        else:
            print("⚠️ RESEND_API_KEY not found. Email sending will fail.")

    def send_email(self, to_email: str, subject: str, html_content: str, from_email: str = "onboarding@strateup.com.br"):
        """
        Sends a transactional email using Resend.
        """
        if not self.api_key:
            print(f"xx Mock Send Email to {to_email}: {subject}")
            return {"id": "mock-id"}

        try:
            params = {
                "from": "StrateUp <" + from_email + ">",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            email = resend.Emails.send(params)
            return email
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            raise e

    def send_welcome_sequence(self, to_email: str, name: str = "Founder"):
        """
        Day 0: The Bait Delivery.
        """
        subject = "seu relatório do espião de funil (strateup)"
        html = f"""
        <h1>Seu Relatório Chegou 🕵️</h1>
        <p>Olá {name},</p>
        <p>Obrigado por usar o <strong>Espião de Funil</strong>.</p>
        <p>Abaixo está o link para o relatório preliminar que geramos:</p>
        <br>
        <a href="https://strateup.com.br/report/demo-123" style="padding: 12px 24px; background-color: #a855f7; color: white; text-decoration: none; border-radius: 5px;">Ver Relatório</a>
        <br><br>
        <p><strong>Dica Rápida:</strong> Percebemos que esse concorrente não está usando Pixel do TikTok. Isso é uma oportunidade para você.</p>
        <p>Amanhã vou te contar como eu quase perdi meu maior cliente por causa de um detalhe bobo.</p>
        <br>
        <p>Abraço,<br>Phill do StrateUp</p>
        """
        return self.send_email(to_email, subject, html)
